"""Usage : python -m asset_audit EXTRACTION.csv --output rapport_local."""
import argparse
import csv
import html
import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from . import __version__
from .engine import ConfigurationError, InputError, audit, load_config, sha256_file


def csv_safe(value):
    text = '' if value is None else str(value)
    # Préserve l'original dans JSON / source ; neutralise les formules à l'ouverture Excel.
    return "'" + text if text.lstrip().startswith(('=', '+', '-', '@', '\t', '\r')) else text


def write_html(result, path):
    esc=lambda v:html.escape(str(v))
    body=[]
    for item in result['variables']:
        needs=' ; '.join(p.get('label',p['reason']) for p in item['pending']) or 'Aucune précision supplémentaire pour les contrôles unitaires définis'
        values=[item['id'],item['variable'],item['filled'],item['blank'],item['format_invalid'],item['technical_status'],needs]
        body.append('<tr><td>'+'</td><td>'.join(esc(v) for v in values)+'</td></tr>')
    html_text="""<!doctype html><html lang="fr"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Audit INVREF</title>
<style>body{font:15px system-ui;margin:32px;color:#18283b}table{border-collapse:collapse;width:100%}td,th{border:1px solid #cbd5df;padding:9px;text-align:left;vertical-align:top}th{background:#edf2f7}h1{color:#163e66}.cards{display:flex;gap:12px;flex-wrap:wrap}.card{padding:16px;background:#edf2f7;border-radius:8px;min-width:150px}.card b{display:block;font-size:24px;color:#163e66}p{max-width:1100px}.table{overflow:auto}summary{cursor:pointer;padding:8px;font-weight:600}</style>
<h1>Audit INVREF — exhaustivité et conformité</h1>"""
    cards=[(str(result['present_variables'])+'/98','variables présentes'),(result['rows'],'lignes contrôlées'),(result['conformity_alerts'],'alertes de conformité'),(result['review_alerts'],'alertes pour revue humaine')]
    html_text+='<div class="cards">'+''.join(f'<div class="card"><b>{esc(v)}</b>{esc(label)}</div>' for v,label in cards)+'</div>'
    html_text+=f'<p><b>Résultat global : {esc(result["status"])}</b>. Référentiel {esc(result["config_version"])} — {result["reviewed_variables"]} variables revues à partir du catalogue.</p>'
    html_text+='<p>La colonne « Contrôles exécutés » présente le résultat des vérifications applicables aux données. Les précisions métier sont séparées : elles ne sont ni des anomalies détectées ni des contrôles réalisés. Les comparaisons entre colonnes et les obligations conditionnelles sont documentées dans controles.csv.</p>'
    html_text+=f'<details><summary>Précisions métier : {result["pending_requirements"]} exigences source restent à paramétrer</summary><p>Ce décompte porte sur les exigences effectivement mentionnées dans le catalogue (listes, formats, longueurs, seuils ou conventions). Il ne compte pas chaque option du programme. Consulter controles.csv pour chaque phrase source et parametres.json pour les décisions et paramètres exacts.</p></details>'
    html_text+='<p>Détail des alertes : <a href="anomalies.csv">anomalies.csv</a>. Traçabilité des contrôles : <a href="controles.csv">controles.csv</a>. <a href="variables.csv">Statistiques des variables</a>.</p>'
    html_text+='<div class="table"><table><thead><tr><th>ID</th><th>Variable</th><th>Renseigné</th><th>Vide</th><th>Cellules non conformes (format/domaine/bornes)</th><th>Contrôles exécutés</th><th>Précisions réellement nécessaires</th></tr></thead><tbody>'+''.join(body)+'</tbody></table></div>'
    html_text+=f'<p>SHA-256 du fichier source : {esc(result["input_sha256"])}. Aucune modification de la source ; toutes les alertes sont soumises à analyse.</p></html>'
    path.write_text(html_text,encoding='utf-8')


def main(argv=None):
    parser=argparse.ArgumentParser(description='Audit local des 98 variables INVREF. Aucun envoi de données.')
    parser.add_argument('input',type=Path)
    parser.add_argument('--config',type=Path,help='Référentiel JSON ; défaut : les 98 variables du catalogue')
    parser.add_argument('--output',type=Path,default=Path('reports/audit'))
    parser.add_argument('--sheet',help='Onglet Excel ; obligatoire si plusieurs onglets')
    parser.add_argument('--header-row',type=int,default=1,help='Ligne/record de l’en-tête (4 pour le modèle catalogue)')
    parser.add_argument('--delimiter',default=';',help='Séparateur CSV, explicite ; défaut point-virgule')
    parser.add_argument('--encoding',default='utf-8-sig')
    args=parser.parse_args(argv)
    temp=None
    try:
        cfg=load_config(args.config)
        if not args.input.is_file():raise InputError('Fichier source introuvable')
        if args.output.exists():raise InputError('Dossier de sortie déjà existant ; choisir un nouveau chemin')
        input_hash=sha256_file(args.input)
        cfg_bytes=json.dumps(cfg,ensure_ascii=False,sort_keys=True).encode()
        import hashlib
        cfg_hash=hashlib.sha256(cfg_bytes).hexdigest()
        args.output.parent.mkdir(parents=True,exist_ok=True)
        temp=Path(tempfile.mkdtemp(prefix='.audit-',dir=args.output.parent))
        columns=['source_line','field','rule_id','issue_type','severity','raw_value','normalized_value','threshold','message','review_status']
        with (temp/'anomalies.csv').open('w',encoding='utf-8-sig',newline='') as stream, (temp/'donnees_normalisees.csv').open('w',encoding='utf-8-sig',newline='') as normalized_stream:
            writer=csv.DictWriter(stream,fieldnames=columns,delimiter=';');writer.writeheader()
            normalized_writer=csv.DictWriter(normalized_stream,fieldnames=['source_line']+[f['name'] for f in cfg['fields']],delimiter=';')
            normalized_writer.writeheader()
            def emit(item):writer.writerow({k:csv_safe(v) for k,v in item.items()})
            def emit_normalized(item):normalized_writer.writerow({k:csv_safe(v) for k,v in item.items()})
            result=audit(args.input,cfg,emit,sheet=args.sheet,header_row=args.header_row,delimiter=args.delimiter,encoding=args.encoding,emit_normalized=emit_normalized)
        if sha256_file(args.input)!=input_hash:raise InputError('Source modifiée pendant le contrôle ; relancer')
        result.update({'tool_version':__version__,'config_version':cfg['version'],'config_sha256':cfg_hash,'input_name':args.input.name,'input_sha256':input_hash,'executed_at':datetime.now(timezone.utc).isoformat(),'import_parameters':{'sheet':args.sheet,'header_row':args.header_row,'delimiter':args.delimiter,'encoding':args.encoding},'scope':'Exhaustivité et conformité unitaires ; aucune cohérence intercolonnes.'})
        (temp/'synthese.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        (temp/'parametres.json').write_text(json.dumps(cfg,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        with (temp/'variables.csv').open('w',encoding='utf-8-sig',newline='') as stream:
            w=csv.writer(stream,delimiter=';');w.writerow(['id','variable','présente','renseigné','vide','taux vide','distinctes','formats invalides','cellules avec alertes','statut','contrôles actifs','exigences source à préciser','résultat contrôles exécutés','politique exhaustivité'])
            for s in result['variables']:
                w.writerow([csv_safe(v) for v in [s['id'],s['variable'],s['present'],s['filled'],s['blank'],s['blank_rate'],s['distinct_values'],s['format_invalid'],s['anomaly_cells'],s['status'],', '.join(s['rules']),' ; '.join(p.get('label',p['reason']) for p in s['pending']),s['technical_status'],s['completeness_policy']]])
        with (temp/'controles.csv').open('w',encoding='utf-8-sig',newline='') as stream:
            w=csv.writer(stream,delimiter=';')
            w.writerow(['id variable','variable','id règle','origine','texte source','état exécution','valeurs testées','contrôles techniques','précisions liées','explication'])
            for rule in result['rule_review']:
                w.writerow([csv_safe(v) for v in [rule['variable_id'],rule['variable'],rule['id'],rule['origin'],rule['source_clause'],rule['execution_status'],rule['tested_values'],', '.join(rule.get('checks',[])),', '.join(rule.get('requirement_ids',[])),rule['note']]])
        write_html(result,temp/'rapport.html')
        os.rename(temp,args.output);temp=None
        print(f"{result['status']} : {result['rows']} lignes, {result['present_variables']}/98 champs, {result['anomalies']} alertes, {result['pending_requirements']} exigences source à préciser. Rapport : {args.output / 'rapport.html'}")
        return 1 if result['anomalies'] else 2 if result['status']!='CONFORME_CONTROLES_EXECUTES' else 0
    except (ConfigurationError,InputError,OSError,ValueError,KeyError,TypeError,csv.Error) as exc:
        print(f'ERREUR : {exc}')
        return 3
    finally:
        if temp is not None:shutil.rmtree(temp)


if __name__=='__main__':raise SystemExit(main())
