"""Tests du lecteur INVREF, des règles configurables et des rapports produits."""

import copy
import csv
import json
import tempfile
import unittest
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from openpyxl import Workbook
from openpyxl.utils.datetime import CALENDAR_MAC_1904

from asset_audit.engine import audit, load_config, validate_config, number, parse_date, isin_valid, ConfigurationError
from asset_audit.__main__ import main, csv_safe


def valid_row(cfg):
    """Fabrique une ligne fictive lisible par les 98 champs du référentiel.

    Les valeurs sont volontairement simples : elles servent de point de départ
    pour injecter une anomalie précise dans chaque test, sans données métier.
    """
    values=[]
    for f in cfg['fields']:
        values.append('20261012' if f['kind']=='date' else '1,25' if f['kind']=='number' else 'EUR' if f['id'] in ('V057','V058') else 'CODE001' if f['kind']=='identifier' else 'OUI' if f['kind']=='indicator' else 'Libellé fictif')
    return values


class AuditTests(unittest.TestCase):
    """Une extraction temporaire par test évite de modifier des fichiers réels."""

    def setUp(self):
        """Charge le paramétrage standard et prépare un dossier isolé."""
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.cfg=load_config()

    def tearDown(self):
        """Supprime les fichiers CSV, Excel et rapports créés pendant le test."""
        self.tmp.cleanup()

    def csv_file(self,rows,headers=None):
        """Écrit les lignes à tester dans un CSV aux conventions de l'outil."""
        p=self.root/'input.csv'
        with p.open('w',encoding='utf-8-sig',newline='') as out:
            w=csv.writer(out,delimiter=';');w.writerow(headers or [f['name'] for f in self.cfg['fields']]);w.writerows(rows)
        return p
    def run_audit(self,rows,cfg=None,headers=None):
        """Lance le moteur et récupère synthèse, alertes et données normalisées."""
        anomalies=[];normalized=[]
        result=audit(self.csv_file(rows,headers),cfg or self.cfg,anomalies.append,emit_normalized=normalized.append)
        return result,anomalies,normalized
    def test_98_catalogue_coverage(self):
        """Les 98 champs sont présents, dans le même ordre que la matrice de suivi."""
        self.assertEqual([f['id'] for f in self.cfg['fields']],[f'V{i:03}' for i in range(1,99)])
        with Path('docs/couverture_variables.csv').open(encoding='utf-8-sig') as stream:
            rows=list(csv.DictReader(stream,delimiter=';'))
        self.assertEqual([r['variable'] for r in rows],[f['name'] for f in self.cfg['fields']])
        result,alerts,norm=self.run_audit([valid_row(self.cfg)])
        self.assertEqual(result['checked_cells'],98);self.assertEqual(result['anomalies'],0)
        self.assertEqual(result['status'],'A_COMPLETER')
        self.assertEqual(len(norm[0]),99)
        self.assertEqual(result['pending_requirements'],92)
        self.assertEqual(result['reviewed_variables'],98)
    def test_invalid_value_on_every_variable(self):
        """Chaque variable détecte au moins une valeur délibérément invalide."""
        # 98 injections indépendantes, sans omettre les dernières variables.
        for i,f in enumerate(self.cfg['fields']):
            with self.subTest(variable=f['name']):
                row=valid_row(self.cfg)
                row[i]='20260230' if f['kind']=='date' else 'NaN' if f['kind']=='number' else 'code\x01parasite'
                result,alerts,_=self.run_audit([row])
                self.assertTrue(any(a['field']==f['name'] for a in alerts))
                self.assertEqual(result['variables'][i]['anomaly_cells'],1)
    def test_required_and_blank_on_every_variable(self):
        """Le moteur sait appliquer l'obligation et compter les vides partout."""
        # On rend tous les champs obligatoires uniquement dans cette copie de test.
        cfg=copy.deepcopy(self.cfg)
        for f in cfg['fields']:f['required']=True
        result,alerts,_=self.run_audit([['']*97+[' ']],cfg)
        required=[a for a in alerts if a['rule_id'].endswith('.REQUIRED')]
        self.assertEqual(len(required),98);self.assertEqual(result['checked_cells'],98)
        for s in result['variables']:self.assertEqual(s['blank'],1);self.assertEqual(s['blank_rate'],1)
    def test_default_required_only_documented(self):
        """La configuration livrée n'impose que les obligations documentées."""
        self.assertEqual([f['id'] for f in self.cfg['fields'] if f['required'] is True],['V001','V006','V057','V058','V075'])
        row=valid_row(self.cfg)
        for i in (0,5,56,57,74):row[i]=' '
        _,alerts,_=self.run_audit([row]);self.assertEqual(len(alerts),5)
    def test_numeric_edge_cases(self):
        """Virgule décimale, groupements et rejets des écritures ambiguës."""
        s=self.cfg['settings']
        for v,expected in [('1 234,56','1234.56'),('-0,25','-0.25'),('1\u202f234,56','1234.56'),('1,2e3','1.2e3'),(0,'0')]:
            self.assertEqual(number(v,s),Decimal(expected))
        for v in ('1 23,4','1.234','1,2,3','NaN','inf','-Infinity','12%','NULL',True,float('nan'),float('inf')):
            with self.subTest(v=v),self.assertRaises(ValueError):number(v,s)
        us=copy.deepcopy(s);us.update(decimal_separator='.',thousands_separator=',')
        self.assertEqual(number('1,234.56',us),Decimal('1234.56'))
        with self.assertRaises(ValueError):number('12,34.56',us)
    def test_dates_strict_and_excel_epochs(self):
        """Dates réelles, année bissextile et calendrier Excel Mac/Windows."""
        s=self.cfg['settings']
        self.assertEqual(parse_date('20240229',s).isoformat(),'2024-02-29')
        self.assertEqual(parse_date('2024-02-29',s).isoformat(),'2024-02-29')
        self.assertEqual(parse_date(20261012,s).isoformat(),'2026-10-12')
        self.assertEqual(parse_date(1,s,CALENDAR_MAC_1904).isoformat(),'1904-01-02')
        for v in ('20260229','20260230','2026-1-2','12/10/2026',46000,True,datetime(2026,1,1,12)):
            with self.subTest(v=v),self.assertRaises(ValueError):parse_date(v,s)
        from openpyxl.utils.datetime import CALENDAR_WINDOWS_1900
        with self.assertRaises(ValueError):parse_date(60,s,CALENDAR_WINDOWS_1900)
    def test_all_configurable_controls(self):
        """Des règles métier renseignées déclenchent les contrôles correspondants."""
        # Cette configuration est fictive : elle prouve le fonctionnement du moteur,
        # sans attribuer ces codes, bornes ou longueurs au référentiel métier.
        cfg=copy.deepcopy(self.cfg)
        f=cfg['fields'][5];f.update(allowed_values=['FR0000120271'],pattern='[A-Z0-9]+',min_length=12,max_length=12,identifier_format='isin',unique=True)
        cfg['fields'][10].update(minimum='0',maximum='2')
        cfg['fields'][24].update(date_min='2026-10-01',date_max='2026-10-31')
        cfg['fields'][1].update(allowed_values=['STOCK'],case='upper',max_blank_rate=0)
        a=valid_row(cfg);a[5]='FR0000120271';a[1]='stock';a[10]='3';a[24]='20260930'
        b=a.copy();b[1]='';b[5]='FR0000120271'
        result,alerts,_=self.run_audit([a,b],cfg)
        codes={a['rule_id'].split('.')[-1] for a in alerts}
        self.assertTrue({'CASE','MAXIMUM','DATE_MIN','DUPLICATE_VALUE','BLANK_RATE'}<=codes)
        self.assertTrue(isin_valid('FR0000120271'));self.assertFalse(isin_valid('FR0000120272'))
        a[5]='a!';_,alerts,_=self.run_audit([a],cfg)
        codes={a['rule_id'].split('.')[-1] for a in alerts}
        self.assertTrue({'DOMAIN','PATTERN','MIN_LENGTH','ISIN'}<=codes)
        a[5]='TOOLONGIDENTIFIER';_,alerts,_=self.run_audit([a],cfg)
        self.assertTrue(any(x['rule_id'].endswith('.MAX_LENGTH') for x in alerts))
    def test_parity_strict_positive_and_negative_amounts(self):
        """La parité doit être positive ; un montant ou taux négatif reste possible."""
        row=valid_row(self.cfg);row[12]='-12,5';row[37]='-0,02';row[61]='0'
        _,alerts,_=self.run_audit([row]);self.assertEqual(len(alerts),1)
        self.assertEqual(alerts[0]['field'],'Parité de change');self.assertTrue(alerts[0]['rule_id'].endswith('.MINIMUM'))
    def test_single_valuation_date(self):
        """Plusieurs dates de valorisation dans une extraction sont signalées."""
        a=valid_row(self.cfg);b=a.copy();b[0]='20261013'
        _,alerts,_=self.run_audit([a,b]);self.assertEqual(len(alerts),1)
        self.assertTrue(alerts[0]['rule_id'].endswith('.MAX_DISTINCT'))
    def test_schema_missing_duplicate_unexpected(self):
        """Colonnes absentes, répétées ou inconnues empêchent un contrôle fictif."""
        h=[f['name'] for f in self.cfg['fields']];h[0]=h[1];h[-1]='INCONNUE'
        result,alerts,_=self.run_audit([valid_row(self.cfg)],headers=h)
        codes={a['rule_id'].split('.')[-1] for a in alerts}
        self.assertTrue({'MISSING_COLUMN','DUPLICATE_HEADER','UNEXPECTED_COLUMN'}<=codes)
        self.assertEqual(result['present_variables'],95)
        self.assertEqual(result['variables'][1]['status'],'NON_EXECUTE')
    def test_csv_multiline_and_width_preserve_line(self):
        """Une cellule sur plusieurs lignes garde la bonne ligne source des alertes."""
        a=valid_row(self.cfg);a[3]='texte\nsuite'
        b=valid_row(self.cfg);b[10]='non numérique';b=b[:-1]
        result,alerts,_=self.run_audit([a,b])
        self.assertEqual(result['rows'],2)
        self.assertTrue(any(x['rule_id'].endswith('.ROW_WIDTH') and x['source_line']==4 for x in alerts))
        self.assertTrue(any(x['field']=='Quantité' and x['source_line']==4 for x in alerts))
    def test_whitespace_case_and_control_char(self):
        """Espaces, casse et caractères de contrôle sont repérés séparément."""
        row=valid_row(self.cfg);row[56]=' eur ';row[5]=' 0012 ';row[6]='abc\tdef'
        _,alerts,norm=self.run_audit([row])
        codes={a['rule_id'].split('.')[-1] for a in alerts}
        self.assertTrue({'WHITESPACE','CASE','CONTROL_CHAR'}<=codes)
        self.assertEqual(norm[0]['Code Valeur'],'0012')
        self.assertEqual(norm[0]['Devise de gestion'],'EUR')
    def test_empty_input_not_passed(self):
        """Un modèle sans données porte le statut NON_EXECUTE."""
        result,alerts,_=self.run_audit([])
        self.assertEqual(result['status'],'NON_EXECUTE');self.assertEqual(result['rows'],0)
        self.assertTrue(any(a['rule_id'].endswith('.EMPTY_INPUT') for a in alerts))
    def test_excel_header_offset_and_formulas(self):
        """Un onglet avec en-tête en ligne 4 est lu sans exécuter les formules."""
        p=self.root/'input.xlsx';w=Workbook();s=w.active;s.title='Données INVREF'
        s.append(['Présentation']);s.append(['']);s.append(['Instructions']);s.append([f['name'] for f in self.cfg['fields']])
        row=valid_row(self.cfg);row[0]=datetime(2026,10,12);row[5]=123;row[10]='=1+1';s.append(row);w.save(p)
        alerts=[];result=audit(p,self.cfg,alerts.append,sheet='Données INVREF',header_row=4)
        self.assertEqual(result['rows'],1)
        self.assertTrue(any(x['rule_id'].endswith('.NUMERIC_CODE_STORAGE') for x in alerts))
        self.assertTrue(any(x['field']=='Quantité' and x['source_line']==5 and 'formule' in x['message'] for x in alerts))
    def test_numeric_distinct_by_value_and_optional_memory_mode(self):
        """1,00 et 1,0 comptent comme même nombre ; l'option mémoire est explicite."""
        cfg=copy.deepcopy(self.cfg);cfg['fields'][10]['unique']=True
        a=valid_row(cfg);b=a.copy();a[10]='1,00';b[10]='1,0'
        result,alerts,_=self.run_audit([a,b],cfg)
        self.assertEqual(result['variables'][10]['distinct_values'],1)
        self.assertTrue(any(x['rule_id']=='V011.DUPLICATE_VALUE' for x in alerts))
        cfg=copy.deepcopy(self.cfg);cfg['settings']['track_distinct']=False
        with self.assertRaises(ConfigurationError):self.run_audit([a],cfg)
        cfg['fields'][0]['max_distinct']=None
        result,_,_=self.run_audit([a],cfg)
        self.assertIsNone(result['variables'][10]['distinct_values'])
        self.assertTrue(any(r['id']=='V001.Q03' and r['execution_status']=='DESACTIVE_PAR_CONFIGURATION' for r in result['rule_review']))
    def test_indicator_boolean_excel(self):
        """Une cellule booléenne Excel est reconnue par une liste autorisée."""
        p=self.root/'boolean.xlsx';w=Workbook();s=w.active
        s.append([f['name'] for f in self.cfg['fields']]);row=valid_row(self.cfg)
        row[17]=True;s.append(row);w.save(p)
        cfg=copy.deepcopy(self.cfg);cfg['fields'][17]['allowed_values']=['TRUE','FALSE']
        alerts=[];result=audit(p,cfg,alerts.append)
        self.assertFalse(any(x['field']==cfg['fields'][17]['name'] for x in alerts))
    def test_config_errors_fail_closed(self):
        """Un référentiel incohérent est rejeté avant de donner un faux résultat."""
        cases=[lambda c:c['fields'].pop(),lambda c:c['fields'][0].update(name=c['fields'][1]['name']),lambda c:c['settings'].update(thousands_separator=','),lambda c:c['fields'][1].update(allowed_values=[]),lambda c:c['fields'][10].update(minimum='3',maximum='2'),lambda c:c['fields'][1].update(required='yes'),lambda c:c['fields'][1].update(max_blank_rate=2),lambda c:c['fields'][10].update(minimum='abc'),lambda c:c['fields'][5].update(pattern='['),lambda c:c['fields'][5].update(minimum='0')]
        for change in cases:
            cfg=copy.deepcopy(self.cfg);change(cfg)
            with self.assertRaises(ConfigurationError):validate_config(cfg)
    def test_cli_reports_and_no_overwrite(self):
        """La commande produit sept rapports et protège ceux qui existent déjà."""
        p=self.csv_file([valid_row(self.cfg)]);out=self.root/'report'
        self.assertEqual(main([str(p),'--output',str(out)]),2)
        self.assertEqual({x.name for x in out.iterdir()},{'rapport.html','anomalies.csv','variables.csv','synthese.json','parametres.json','donnees_normalisees.csv','controles.csv'})
        result=json.loads((out/'synthese.json').read_text());self.assertEqual(len(result['variables']),98)
        self.assertEqual(len(result['input_sha256']),64)
        self.assertEqual(main([str(p),'--output',str(out)]),3)
        self.assertEqual(csv_safe('=HYPERLINK("x")'),'\'=HYPERLINK("x")')
    def test_fully_configured_can_pass(self):
        """Après paramétrage des 92 exigences, un jeu fictif peut être validé."""
        # Les paramètres ci-dessous sont des exemples de test, pas des valeurs
        # approuvées : le test ne constitue pas une recette métier INVREF.
        cfg=copy.deepcopy(self.cfg)
        for f in cfg['fields']:
            for requirement in f['pending']:
                key=requirement['parameter']
                if key=='domain':f['allowed_values']=[valid_row(cfg)[int(f['id'][1:])-1]]
                elif key=='identifier_pattern':f['pattern']='[A-Za-z0-9]+'
                elif key=='identifier_length':f['max_length']=100
                elif key=='numeric_limits':f['maximum']='100'
                elif key=='sign_convention':f['sign_convention']='any'
                else:self.fail('Exigence non prise en charge '+key)
        result,alerts,_=self.run_audit([valid_row(cfg)],cfg)
        self.assertEqual(alerts,[]);self.assertEqual(result['status'],'CONFORME_CONTROLES_EXECUTES')
        self.assertEqual(result['pending_requirements'],0)
        self.assertNotIn('A_PRECISER',result['source_rule_counts'])
    def test_source_review_covers_every_quality_clause(self):
        """Chaque phrase de qualité du catalogue figure dans la revue tracée."""
        for f in self.cfg['fields']:
            with self.subTest(field=f['name']):
                source=[x.strip() for x in f['source_quality'].split(';') if x.strip()]
                reviewed=[x['source_clause'] for x in f['rule_review'] if x['origin']=='Contrôle de qualité']
                self.assertEqual(source,reviewed)
                for need in f['pending']:
                    self.assertIn(need['source_clause'],source)
                self.assertEqual(f['source_row'],int(f['id'][1:])+1)
    def test_no_invented_pending_options(self):
        """Le registre en attente ne réintroduit pas d'obligations arbitraires."""
        for f in self.cfg['fields']:
            for need in f['pending']:
                self.assertNotIn(need['parameter'],('required','date_min','date_max','minimum','maximum','min_length','max_length'))
        for n in (1,11,16,24,25,30,57,58,62,63,65,87,93,94,95,98):
            self.assertEqual(self.cfg['fields'][n-1]['pending'],[],n)
        self.assertEqual({p['parameter'] for p in self.cfg['fields'][2]['pending']},{'identifier_pattern','identifier_length'})
        self.assertIsNone(self.cfg['fields'][2]['allowed_values'])
    def test_positive_coefficients_and_nominal_from_source(self):
        """Les quatre contraintes strictement positives issues du catalogue agissent."""
        for n in (36,37,56,62):
            for value in ('0','-1'):
                with self.subTest(field=n,value=value):
                    row=valid_row(self.cfg);row[n-1]=value
                    _,alerts,_=self.run_audit([row])
                    self.assertTrue(any(a['rule_id']==f'V{n:03}.MINIMUM' for a in alerts))
    def test_currency_reference_is_membership_not_only_shape(self):
        """Une devise doit appartenir à la liste ISO, pas seulement avoir 3 lettres."""
        row=valid_row(self.cfg);row[56]='ZZZ';row[57]='XOF'
        _,alerts,_=self.run_audit([row])
        self.assertTrue(any(a['rule_id']=='V057.DOMAIN' for a in alerts))
        self.assertFalse(any(a['field']=='Devise portefeuille' for a in alerts))
        self.assertEqual(self.cfg['fields'][56]['reference']['publication'],'2026-09-17')
    def test_case_variants_without_canonical_reference(self):
        """Deux graphies du même code sont détectées sans casse métier imposée."""
        a=valid_row(self.cfg);b=a.copy();a[1]='STOCK';b[1]='stock'
        _,alerts,_=self.run_audit([a,b])
        self.assertTrue(any(x['rule_id']=='V002.CASE_VARIANT' for x in alerts))
    def test_isin_candidates_are_reviewed_without_forcing_internal_codes(self):
        """Un ISIN probable invalide est à revoir ; un code interne reste permis."""
        row=valid_row(self.cfg);row[5]='FR0000120272'
        result,alerts,_=self.run_audit([row])
        self.assertTrue(any(a['rule_id']=='V006.ISIN_CANDIDATE' and a['issue_type']=='REVUE' for a in alerts))
        self.assertEqual(result['review_alerts'],1)
        self.assertEqual(result['conformity_alerts'],0)
        row[5]='INTERNE42';_,alerts,_=self.run_audit([row])
        self.assertFalse(any(a['field']=='Code Valeur' for a in alerts))
    def test_sign_convention_and_reviewer_alerts(self):
        """Signe configuré = conformité ; signes suspects = revue humaine."""
        cfg=copy.deepcopy(self.cfg);cfg['fields'][13]['sign_convention']='nonpositive'
        row=valid_row(cfg);row[13]='2'
        _,alerts,_=self.run_audit([row],cfg)
        self.assertTrue(any(a['rule_id']=='V014.SIGN_CONVENTION' for a in alerts))
        row=valid_row(self.cfg);row[10]='-1';row[49]='-1'
        result,alerts,_=self.run_audit([row])
        self.assertEqual(result['review_alerts'],2)
        self.assertTrue(all(a['issue_type']=='REVUE' for a in alerts))
    def test_source_directed_label_required(self):
        """La directive V074 rend obligatoire le libellé associé V075."""
        row=valid_row(self.cfg);row[74]=''
        _,alerts,_=self.run_audit([row])
        self.assertTrue(any(a['rule_id']=='V075.REQUIRED' for a in alerts))
    def test_waiver_requires_reason_and_approver(self):
        """Une exigence écartée requiert motif et approbateur identifiés."""
        cfg=copy.deepcopy(self.cfg)
        need=cfg['fields'][1]['pending'][0]
        need['waiver']={'reason':'Non applicable au périmètre','approved_by':'Référent fictif'}
        result,_,_=self.run_audit([valid_row(cfg)],cfg)
        self.assertEqual(result['pending_requirements'],91)
        self.assertTrue(any(r['execution_status']=='NON_APPLICABLE_JUSTIFIE' for r in result['rule_review']))
        need['waiver']={'reason':'test'}
        with self.assertRaises(ConfigurationError):validate_config(cfg)
    def test_invisible_character_and_separate_report_status(self):
        """Un caractère invisible est détecté ; technique et métier restent distincts."""
        row=valid_row(self.cfg);row[5]='AB\u200b12'
        result,alerts,_=self.run_audit([row])
        self.assertTrue(any(a['rule_id']=='V006.CONTROL_CHAR' for a in alerts))
        self.assertEqual(result['variables'][5]['format_invalid'],1)
        self.assertEqual(result['variables'][1]['technical_status'],'OK_CONTROLES_EXECUTES')
        self.assertEqual(result['variables'][1]['reference_status'],'A_PRECISER')
        result,_,_=self.run_audit([])
        self.assertFalse(any(r['execution_status']=='CONTROLE_EXECUTE' for r in result['rule_review']))



if __name__=='__main__':unittest.main()
