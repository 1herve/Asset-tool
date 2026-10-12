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
    values=[]
    for f in cfg['fields']:
        values.append('20261012' if f['kind']=='date' else '1,25' if f['kind']=='number' else 'EUR' if f['id'] in ('V057','V058') else 'CODE001' if f['kind']=='identifier' else 'OUI' if f['kind']=='indicator' else 'Libellé fictif')
    return values


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.cfg=load_config()
    def tearDown(self):self.tmp.cleanup()
    def csv_file(self,rows,headers=None):
        p=self.root/'input.csv'
        with p.open('w',encoding='utf-8-sig',newline='') as out:
            w=csv.writer(out,delimiter=';');w.writerow(headers or [f['name'] for f in self.cfg['fields']]);w.writerows(rows)
        return p
    def run_audit(self,rows,cfg=None,headers=None):
        anomalies=[];normalized=[]
        result=audit(self.csv_file(rows,headers),cfg or self.cfg,anomalies.append,emit_normalized=normalized.append)
        return result,anomalies,normalized
    def test_98_catalogue_coverage(self):
        self.assertEqual([f['id'] for f in self.cfg['fields']],[f'V{i:03}' for i in range(1,99)])
        with Path('docs/couverture_variables.csv').open() as stream:
            rows=list(csv.DictReader(stream))
        self.assertEqual([r['variable'] for r in rows],[f['name'] for f in self.cfg['fields']])
        result,alerts,norm=self.run_audit([valid_row(self.cfg)])
        self.assertEqual(result['checked_cells'],98);self.assertEqual(result['anomalies'],0)
        self.assertEqual(result['status'],'A_COMPLETER')
        self.assertEqual(len(norm[0]),99)
        self.assertEqual(result['pending_parameters'],284)
    def test_invalid_value_on_every_variable(self):
        # 98 injections indépendantes, sans omettre les dernières variables.
        for i,f in enumerate(self.cfg['fields']):
            with self.subTest(variable=f['name']):
                row=valid_row(self.cfg)
                row[i]='20260230' if f['kind']=='date' else 'NaN' if f['kind']=='number' else 'code\x00parasite'
                result,alerts,_=self.run_audit([row])
                self.assertTrue(any(a['field']==f['name'] for a in alerts))
                self.assertEqual(result['variables'][i]['anomaly_cells'],1)
    def test_required_and_blank_on_every_variable(self):
        cfg=copy.deepcopy(self.cfg)
        for f in cfg['fields']:f['required']=True
        result,alerts,_=self.run_audit([['']*97+[' ']],cfg)
        required=[a for a in alerts if a['rule_id'].endswith('.REQUIRED')]
        self.assertEqual(len(required),98);self.assertEqual(result['checked_cells'],98)
        for s in result['variables']:self.assertEqual(s['blank'],1);self.assertEqual(s['blank_rate'],1)
    def test_default_required_only_documented(self):
        self.assertEqual([f['id'] for f in self.cfg['fields'] if f['required'] is True],['V001','V006','V057','V058'])
        row=valid_row(self.cfg)
        for i in (0,5,56,57):row[i]=' '
        _,alerts,_=self.run_audit([row]);self.assertEqual(len(alerts),4)
    def test_numeric_edge_cases(self):
        s=self.cfg['settings']
        for v,expected in [('1 234,56','1234.56'),('-0,25','-0.25'),('1\u202f234,56','1234.56'),('1,2e3','1.2e3'),(0,'0')]:
            self.assertEqual(number(v,s),Decimal(expected))
        for v in ('1 23,4','1.234','1,2,3','NaN','inf','-Infinity','12%','NULL',True,float('nan'),float('inf')):
            with self.subTest(v=v),self.assertRaises(ValueError):number(v,s)
        us=copy.deepcopy(s);us.update(decimal_separator='.',thousands_separator=',')
        self.assertEqual(number('1,234.56',us),Decimal('1234.56'))
        with self.assertRaises(ValueError):number('12,34.56',us)
    def test_dates_strict_and_excel_epochs(self):
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
        row=valid_row(self.cfg);row[12]='-12,5';row[37]='-0,02';row[61]='0'
        _,alerts,_=self.run_audit([row]);self.assertEqual(len(alerts),1)
        self.assertEqual(alerts[0]['field'],'Parité de change');self.assertTrue(alerts[0]['rule_id'].endswith('.MINIMUM'))
    def test_single_valuation_date(self):
        a=valid_row(self.cfg);b=a.copy();b[0]='20261013'
        _,alerts,_=self.run_audit([a,b]);self.assertEqual(len(alerts),1)
        self.assertTrue(alerts[0]['rule_id'].endswith('.MAX_DISTINCT'))
    def test_schema_missing_duplicate_unexpected(self):
        h=[f['name'] for f in self.cfg['fields']];h[0]=h[1];h[-1]='INCONNUE'
        result,alerts,_=self.run_audit([valid_row(self.cfg)],headers=h)
        codes={a['rule_id'].split('.')[-1] for a in alerts}
        self.assertTrue({'MISSING_COLUMN','DUPLICATE_HEADER','UNEXPECTED_COLUMN'}<=codes)
        self.assertEqual(result['present_variables'],95)
        self.assertEqual(result['variables'][1]['status'],'NON_EXECUTE')
    def test_csv_multiline_and_width_preserve_line(self):
        a=valid_row(self.cfg);a[3]='texte\nsuite'
        b=valid_row(self.cfg);b[10]='non numérique';b=b[:-1]
        result,alerts,_=self.run_audit([a,b])
        self.assertEqual(result['rows'],2)
        self.assertTrue(any(x['rule_id'].endswith('.ROW_WIDTH') and x['source_line']==4 for x in alerts))
        self.assertTrue(any(x['field']=='Quantité' and x['source_line']==4 for x in alerts))
    def test_whitespace_case_and_control_char(self):
        row=valid_row(self.cfg);row[56]=' eur ';row[5]=' 0012 ';row[6]='abc\tdef'
        _,alerts,norm=self.run_audit([row])
        codes={a['rule_id'].split('.')[-1] for a in alerts}
        self.assertTrue({'WHITESPACE','CASE','CONTROL_CHAR'}<=codes)
        self.assertEqual(norm[0]['Code Valeur'],'0012')
        self.assertEqual(norm[0]['Devise de gestion'],'EUR')
    def test_empty_input_not_passed(self):
        result,alerts,_=self.run_audit([])
        self.assertEqual(result['status'],'NON_EXECUTE');self.assertEqual(result['rows'],0)
        self.assertTrue(any(a['rule_id'].endswith('.EMPTY_INPUT') for a in alerts))
    def test_excel_header_offset_and_formulas(self):
        p=self.root/'input.xlsx';w=Workbook();s=w.active;s.title='Données INVREF'
        s.append(['Présentation']);s.append(['']);s.append(['Instructions']);s.append([f['name'] for f in self.cfg['fields']])
        row=valid_row(self.cfg);row[0]=datetime(2026,10,12);row[5]=123;row[10]='=1+1';s.append(row);w.save(p)
        alerts=[];result=audit(p,self.cfg,alerts.append,sheet='Données INVREF',header_row=4)
        self.assertEqual(result['rows'],1)
        self.assertTrue(any(x['rule_id'].endswith('.NUMERIC_CODE_STORAGE') for x in alerts))
        self.assertTrue(any(x['field']=='Quantité' and x['source_line']==5 and 'formule' in x['message'] for x in alerts))
    def test_numeric_distinct_by_value_and_optional_memory_mode(self):
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
    def test_indicator_boolean_excel(self):
        p=self.root/'boolean.xlsx';w=Workbook();s=w.active
        s.append([f['name'] for f in self.cfg['fields']]);row=valid_row(self.cfg)
        row[17]=True;s.append(row);w.save(p)
        cfg=copy.deepcopy(self.cfg);cfg['fields'][17]['allowed_values']=['TRUE','FALSE']
        alerts=[];result=audit(p,cfg,alerts.append)
        self.assertFalse(any(x['field']==cfg['fields'][17]['name'] for x in alerts))
    def test_config_errors_fail_closed(self):
        cases=[lambda c:c['fields'].pop(),lambda c:c['fields'][0].update(name=c['fields'][1]['name']),lambda c:c['settings'].update(thousands_separator=','),lambda c:c['fields'][1].update(allowed_values=[]),lambda c:c['fields'][10].update(minimum='3',maximum='2'),lambda c:c['fields'][1].update(required='yes'),lambda c:c['fields'][1].update(max_blank_rate=2),lambda c:c['fields'][10].update(minimum='abc'),lambda c:c['fields'][5].update(pattern='['),lambda c:c['fields'][5].update(minimum='0')]
        for change in cases:
            cfg=copy.deepcopy(self.cfg);change(cfg)
            with self.assertRaises(ConfigurationError):validate_config(cfg)
    def test_cli_reports_and_no_overwrite(self):
        p=self.csv_file([valid_row(self.cfg)]);out=self.root/'report'
        self.assertEqual(main([str(p),'--output',str(out)]),2)
        self.assertEqual({x.name for x in out.iterdir()},{'rapport.html','anomalies.csv','variables.csv','synthese.json','parametres.json','donnees_normalisees.csv'})
        result=json.loads((out/'synthese.json').read_text());self.assertEqual(len(result['variables']),98)
        self.assertEqual(len(result['input_sha256']),64)
        self.assertEqual(main([str(p),'--output',str(out)]),3)
        self.assertEqual(csv_safe('=HYPERLINK("x")'),'\'=HYPERLINK("x")')
    def test_fully_configured_can_pass(self):
        cfg=copy.deepcopy(self.cfg)
        # Compléter le registre (démonstration technique, aucune autorité métier).
        for f in cfg['fields']:
            for p in f['pending']:
                key=p['parameter']
                defaults={'required':False,'allowed_values':[valid_row(cfg)[int(f['id'][1:])-1]],'pattern':'.+','min_length':1,'max_length':100,'minimum':'-100','maximum':'100','date_min':'2000-01-01','date_max':'2100-01-01','identifier_format':None}
                if key=='identifier_format':f['pending']=[p for p in f['pending'] if p['parameter']!=key]
                else:f[key]=defaults[key]
        result,alerts,_=self.run_audit([valid_row(cfg)],cfg)
        self.assertEqual(alerts,[]);self.assertEqual(result['status'],'CONFORME_CONTROLES_EXECUTES')


if __name__=='__main__':unittest.main()
