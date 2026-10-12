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
    rows=''.join('<tr><td>'+ '</td><td>'.join(esc(x) for x in [s['id'],s['variable'],s['filled'],s['blank'],s['format_invalid'],s['status'],', '.join(p['parameter'] for p in s['pending'])])+'</td></tr>' for s in result['variables'])
    path.write_text('''<!doctype html><html lang="fr"><meta charset="utf-8"><title>Audit INVREF</title>
<style>body{font:15px system-ui;margin:36px;color:#18283b}table{border-collapse:collapse;width:100%}td,th{border:1px solid #cbd5df;padding:8px;text-align:left}th{background:#edf2f7}h1{color:#163e66}p{max-width:1000px}</style>
<h1>Audit INVREF — exhaustivité et conformité</h1>'''+f'<p><b>Statut : {esc(result["status"])}</b> | {result["rows"]} lignes | {result["present_variables"]}/98 variables présentes | {result["anomalies"]} alertes | {result["pending_parameters"]} paramètres manquants.</p>'+
'<p>Les contrôles intercolonnes sont exclus. Une absence d’anomalies ne valide pas les contrôles en attente. Toutes les alertes sont soumises à la revue de l’auditeur. Détails : anomalies.csv ; traçabilité et paramètres : synthese.json et parametres.json.</p>'+
f'<p>Référentiel : {esc(result["config_version"])} — SHA-256 source : {esc(result["input_sha256"])}</p>'+
'<table><thead><tr><th>ID</th><th>Variable</th><th>Renseigné</th><th>Vide</th><th>Format invalide</th><th>Statut</th><th>À paramétrer</th></tr></thead><tbody>'+rows+'</tbody></table></html>',encoding='utf-8')


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
        columns=['source_line','field','rule_id','severity','raw_value','normalized_value','threshold','message','review_status']
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
            w=csv.writer(stream,delimiter=';');w.writerow(['id','variable','présente','renseigné','vide','taux vide','distinctes','formats invalides','cellules avec alertes','statut','contrôles actifs','paramètres manquants'])
            for s in result['variables']:
                w.writerow([csv_safe(v) for v in [s['id'],s['variable'],s['present'],s['filled'],s['blank'],s['blank_rate'],s['distinct_values'],s['format_invalid'],s['anomaly_cells'],s['status'],', '.join(s['rules']),', '.join(p['parameter'] for p in s['pending'])]])
        write_html(result,temp/'rapport.html')
        os.rename(temp,args.output);temp=None
        print(f"{result['status']} : {result['rows']} lignes, {result['present_variables']}/98 champs, {result['anomalies']} alertes, {result['pending_parameters']} paramètres en attente. Rapport : {args.output / 'rapport.html'}")
        return 1 if result['anomalies'] else 2 if result['status']!='CONFORME_CONTROLES_EXECUTES' else 0
    except (ConfigurationError,InputError,OSError,ValueError,KeyError,TypeError,csv.Error) as exc:
        print(f'ERREUR : {exc}')
        return 3
    finally:
        if temp is not None:shutil.rmtree(temp)


if __name__=='__main__':raise SystemExit(main())
