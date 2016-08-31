from utils import workflowInfo, siteInfo, monitor_dir, global_SI
import json
import sys
from collections import defaultdict
from assignSession import *


def parse_one(url, wfn):

    SI = global_SI()
    wfi = workflowInfo( url , wfn)
    where_to_run, missing_to_run,missing_to_run_at = wfi.getRecoveryInfo()       
    err= wfi.getWMErrors()

    print "will be willing to run at"      
    print json.dumps( where_to_run , indent=2)         
    print json.dumps(missing_to_run , indent=2)        
    print json.dumps(missing_to_run_at , indent=2)        
    
    task_error_site_count ={}
    one_explanation = defaultdict(set)


    tasks = err.keys()
    tasks.sort()
    if not tasks:
        return task_error_site_count
        
    html="<html> %s <br><hr><br>"%(tasks[0].split('/')[1])
    
    for task in tasks:  

        #is the task relevant to recover (discard log, cleanup)
        if any([v in task.lower() for v in ['logcol','cleanup']]): continue


        total_count= defaultdict(int)
        error_site_count = defaultdict( lambda : defaultdict(int))
        print err[task].keys()
        for exittype in err[task]:
            #print "\t",err[task][exittype].keys()
            for errorcode_s in err[task][exittype]:
                if errorcode_s == '0' : continue
                #print "\t\t",err[task][exittype][errorcode_s].keys()
                for site in err[task][exittype][errorcode_s]:

                    count = err[task][exittype][errorcode_s][site]['errorCount']
                    total_count[errorcode_s] += count
                    error_site_count[errorcode_s][site] += count
                    for sample in err[task][exittype][errorcode_s][site]['samples']:
                        for step in sample['errors']:
                            for report in  sample['errors'][step]:
                                if report['type'] == 'CMSExeption': continue
                                #if int(report['exitCode']) == int(errorcode_s):
                                one_explanation[errorcode_s].add("%s (Exit code: %s) \n%s"%(report['type'], report['exitCode'], report['details']))
                                #one_explanation[errorcode_s].add( report['details'] )
                                #else:
                                #one_explanation[
        print task
        #print json.dumps( total_count, indent=2)
        #print json.dumps( explanations , indent=2)
        all_sites = set()
        all_codes = set()
        for code in error_site_count:
            for site in error_site_count[code]:
                all_sites.add( site )
                if code != '0':
                    all_codes.add( code)

        #success = total_count['0']
        #total_jobs = sum(total_count.values())
        #print total_jobs,"jobs in total,",success,"successes"
        miss = "{:,}".format(missing_to_run[task]) if task in missing_to_run else "N/A"
        html += "%s is missing %s events"%(task.split('/')[-1], miss)
        html += "<br><table border=1><thead><tr><th>Sites/Errors</th>"
        #for site in all_sites:
        #    html+='<th>%s</th>'%site
        for code in sorted(all_codes):
            html+='<th><a href="#%s">%s</a></th>'%(code,code)
        html+='<th>Site Ready</th>'
        html+='</tr></thead>\n'
        for site in all_sites:
            site_in = 'Yes' if site in SI.sites_ready else 'No'
            color = 'bgcolor=red' if not site in SI.sites_ready else 'bgcolor=lightblue'
            html+='<tr><td %s>%s</td>'%(color,site)
            for code in sorted(all_codes):
                html += '<td %s width=100>%d</td>'% (color,error_site_count[code][site])
            html += '<td %s>%s</td>'% (color, site_in)
            html +='</tr>\n'
        html+='</table><br>'
        task_error_site_count[task] = error_site_count

    html += '<hr><br>'
    html += '<table border=1>'
    for code in one_explanation:
        html +='<tr><td><a name="%s">%s</a></td><td>%s</td></tr>'% ( code, code, '<br><br>'.join(one_explanation[code]).replace('\n','<br>' ))
        #explanations[code].update( one_explanation[code] )
    html+='</table>'
    html+=('<br>'*30)
    html +='</html>'
    wfi.sendLog( 'error', html, show=False)
    fn = '%s'% wfn
    open('%s/report/%s'%(monitor_dir,fn),'w').write( html )

    return task_error_site_count, one_explanation

def parse_all(url):
    explanations = defaultdict(set)
    alls={}
    for wfo in session.query(Workflow).filter(Workflow.status == 'assistance-manual').all():    
        task_error, one_explanation = parse_one( url, wfo.name)
        alls.update( task_error )
        for code in one_explanation:
            explanations[code].update( one_explanation[code] )

    open('%s/all_errors.json'%monitor_dir,'w').write( json.dumps(alls , indent=2 ))

    explanations = dict([(k,list(v)) for k,v in explanations.items()])

    open('%s/explanations.json'%monitor_dir,'w').write( json.dumps(explanations, indent=2))

    alls = json.loads( open('all_errors.json').read())

    affected=set()
    per_code = defaultdict(set)
    for task in alls:
        for code in alls[task]:
            per_code[code].add( task.split('/')[1])
        
    for code in per_code:
        print code
        print json.dumps( sorted(per_code[code]), indent=2)


if __name__=="__main__":
    url = 'cmsweb.cern.ch'

    if len(sys.argv)>1:
        parse_one(url, sys.argv[1])
    else:
        parse_all(url)
