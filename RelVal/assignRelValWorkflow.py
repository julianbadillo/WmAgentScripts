#!/usr/bin/env python -u
from xml.dom import minidom
import urllib2,urllib, httplib, sys, re, os
import json
import optparse


from das_client import get_data
das_host='https://cmsweb.cern.ch'

dbs3_url = 'https://cmsweb.cern.ch'

def getDBSApi():
    """
    Instantiate the DBS3 Client API
    """
    if 'testbed' in dbs3_url:
        dbs3_url_reader = dbs3_url + '/dbs/int/global/DBSReader'
    else:
        dbs3_url_reader = dbs3_url + '/dbs/prod/global/DBSReader'
        
    #this needs to come after /data/srv/wmagent/current/apps/wmagent/etc/profile.d/init.sh is sourced
    from dbs.apis.dbsClient import DbsApi

    dbsApi = DbsApi(url = dbs3_url_reader)
    return dbsApi

def checkDatasetExistenceDAS(dataset):
    query="dataset dataset="+dataset+" status=*"
    das_data = get_data(das_host,query,0,0,0)
    if isinstance(das_data, basestring):
        result = json.loads(das_data)
    else:
        result = das_data
    if result['status'] == 'fail' :
        print 'DAS query failed with reason:',result['reason']
    if len(result['data'])==0:
	return False
    else:
	return True


def assignRequest(url,workflow,team,site,era,procstr,procver,activity,lfn,maxrss):

    params = {"action": "Assign",
              "Team"+team: "checked",
              "SiteWhitelist": site,
              "SiteBlacklist": [],
              "MergedLFNBase": lfn,
              "UnmergedLFNBase": "/store/unmerged",
              "MinMergeSize": 2147483648,
              "MaxMergeSize": 4294967296,
              "MaxMergeEvents": 100000,
              #"maxRSS": 4911724,
              "MaxRSS": maxrss,
              "MaxVSize": 20294967,
              "AcquisitionEra": era,
              "ProcessingString": procstr,
              "ProcessingVersion": procver,
              "Dashboard": activity,
              "useSiteListAsLocation" : True,   ### when we want to use xrootd to readin input files
      #        "CustodialSites": ['T1_US_FNAL'],
      #        "NonCustodialSites": ['T2_CH_CERN'],
      #        "AutoApproveSubscriptionSites": ['T1_US_FNAL'],
      #        "SubscriptionPriority": "Medium",
      #        "CustodialSubType" : "Replica",
              "BlockCloseMaxWaitTime" : 28800,
              "BlockCloseMaxFiles" : 500,
              "BlockCloseMaxEvents" : 20000000,
              "BlockCloseMaxSize" : 5000000000000,
              "SoftTimeout" : 129600,
              "GracePeriod" : 1000,
              "checkbox"+workflow: "checked"}
    # Once the AcqEra is a dict, I have to make it a json objet 
    jsonEncodedParams = {}
    for paramKey in params.keys():    
        jsonEncodedParams[paramKey] = json.dumps(params[paramKey])

    encodedParams = urllib.urlencode(jsonEncodedParams, False)

    headers  =  {"Content-type": "application/x-www-form-urlencoded",
                 "Accept": "text/plain"}

    conn  =  httplib.HTTPSConnection(url, cert_file = os.getenv('X509_USER_PROXY'), key_file = os.getenv('X509_USER_PROXY'))
    conn.request("POST",  "/reqmgr/assign/handleAssignmentPage", encodedParams, headers)
    response = conn.getresponse()
    if response.status != 200:
        os.system('echo '+workflow+' | mail -s \"assignRelValWorkflow.py error 1\" andrew.m.levin@vanderbilt.edu --')
        print 'could not assign request with following parameters:'
        for item in params.keys():
            print item + ": " + str(params[item])
        print 'Response from http call:'
        print 'Status:',response.status,'Reason:',response.reason
        print 'Explanation:'
        data = response.read()
        print data
        print "Exiting!"
  	sys.exit(1)
    conn.close()
    print 'Assigned workflow:',workflow,'to site:',site,'and team',team
    return

def getRequestDict(url, workflow):
    conn  =  httplib.HTTPSConnection(url, cert_file = os.getenv('X509_USER_PROXY'), key_file = os.getenv('X509_USER_PROXY'))
    r1=conn.request("GET",'/reqmgr/reqMgr/request?requestName='+workflow)
    r2=conn.getresponse()
    request = json.loads(r2.read())
    return request


def main():
    url='cmsweb.cern.ch'	
    ### Example: python assignWorkflow.py -w amaltaro_RVZTT_120404_163607_6269 -t testbed-relval -s T1_US_FNAL -e CMSSW_6_0_0_pre1_FS_TEST_WMA -p v1 -a relval -l /store/backfill/1
    parser = optparse.OptionParser()
    parser.add_option('-w', '--workflow', help='Workflow Name',dest='workflow')
    parser.add_option('-t', '--team', help='Type of Requests',dest='team')
    parser.add_option('-s', '--site', help='Site',dest='site')
    parser.add_option('-p', '--procversion', help='Processing Version',dest='procversion')
    parser.add_option('-a', '--activity', help='Dashboard Activity',dest='activity')
    parser.add_option('-l', '--lfn', help='Merged LFN base',dest='lfn')
    parser.add_option('--correct_env',action="store_true",dest='correct_env')
    parser.add_option('--special', help='Use it for special workflows. You also have to change the code according to the type of WF',dest='special')
    parser.add_option('--high_memory', action="store_true",help='Changes the memory at which wmagent kills the jobs',dest='high_memory')
    parser.add_option('--test',action="store_true", help='Nothing is injected, only print infomation about workflow and AcqEra',dest='test')
    parser.add_option('--pu',action="store_true", help='Use it to inject PileUp workflows only',dest='pu')
    parser.add_option('--lsf',action="store_true", help='Use it to assign work to the LSF agent at CERN - vocms174, relvallsf team',dest='lsf')
    parser.add_option('--hi',action="store_true", help='Change the lfn to /store/hirelval/ ',dest='hi')
    (options,args) = parser.parse_args()

    command=""
    for arg in sys.argv:
        command=command+arg+" "

    if not options.correct_env:
        os.system("source /cvmfs/grid.cern.ch/emi-ui-3.7.3-1_sl6v2/etc/profile.d/setup-emi3-ui-example.sh; export X509_USER_PROXY=/tmp/x509up_u13536; source /tmp/relval/sw/comp.pre/slc6_amd64_gcc481/cms/dbs3-client/3.2.8a/etc/profile.d/init.sh; python2.6 "+command + "--correct_env")
        sys.exit(0)

    data = False
    fastsim = False

    if not options.workflow:
        print "The workflow name is mandatory!"
        print "Usage: python assignRelValWorkflow.py -w <requestName>"
        sys.exit(0);
    workflow=options.workflow
    team='relval'
    site='T1_US_FNAL'
    procversion=1
    #procversion='v1'
    activity='relval'
    if options.hi:
        lfn='/store/hirelval/'
    else:    
        lfn='/store/relval'
    procstring = {}
    specialStr = ''

    ### Getting the original dictionary
    schema = getRequestDict(url,workflow)

    if 'type' in schema and schema['type'] == 'HTTPError':
        os.system('echo '+workflow+' | mail -s \"assignRelValWorkflow.py error 2\" andrew.m.levin@vanderbilt.edu --')
        sys.exit(1)

    ### Dropping 2010 HeavyIon workflows or assigning 2011 to CERN/LSF 
    if 'RunHI2010' in schema['RequestString']:
        print workflow, '\t\tHEAVY ION CANNOT RUN AT FNAL --> REQUEST DROPPED!'
        sys.exit(0);
    elif 'RunHI2011' in schema['RequestString']:
        site='T2_CH_CERN'

    # If it's a MC or FS workflow, then assign it to T2_CH_CERN 
    if 'START' in schema['GlobalTag'] or 'POSTLS' in schema['GlobalTag']:
        site='T2_CH_CERN'
    elif 'PRE_SH' in schema['GlobalTag'] or 'PRE_ST' in schema['GlobalTag'] or 'RD53' in schema['GlobalTag']:
        site='T2_CH_CERN'

    # Setting the AcquisitionEra parameter - it will be always the same for all tasks inside the request
    acqera = schema['CMSSWVersion']

    # Handling the parameters given in the command line
    if options.team:
        team=options.team
    if options.site:
        site=options.site
    if options.procversion:
        procversion=int(options.procversion)
    if options.activity:
        activity=options.activity
    if options.lfn:
        lfn=options.lfn


    # Setting the ProcessingString values per Task 
    for key, value in schema.items():
        if type(value) is dict and key.startswith("Task"):
            try:
                if 'ProcessingString' in value:
                    procstring[value['TaskName']] = value['ProcessingString'].replace("-","_")
                elif 'AcquisitionEra' in value and '-' in value['AcquisitionEra']:
                    #procstring[value['TaskName']] = value['AcquisitionEra'].split'-')[-1]
                    procstring[value['TaskName']] = value['AcquisitionEra'].split(schema['CMSSWVersion']+'-')[-1]
                    procstring[value['TaskName']] = procstring[value['TaskName']].replace("-","_")
                    #procstring[value['TaskName']] = 'START61_V8'
                else:
                    good=bad
            except KeyError:
                print "This request has no ProcessingString defined into the Tasks, aborting..."
                sys.exit(1)

            if value['KeepOutput']:
                if 'InputDataset' in value:
                    dset="/" + value['InputDataset'].split('/')[1] + "/" + value['AcquisitionEra'] + "-" + value['ProcessingString'] + "-v" + str(procversion)+"/*"
                elif 'PrimaryDataset' in value:
                    dset="/" + value['PrimaryDataset'] + "/" + value['AcquisitionEra'] + "-" + value['ProcessingString'] + "-v" + str(procversion)+"/*"
                else:
                    #this is normal for Tasks after Task1 
                    #print "not checking if the output dataset of this task exists"
                    continue


                
                #print "checking if the output dataset of this task exists"
                dbsApi = getDBSApi()
                if len(dbsApi.listDatasets(dataset = dset)) != 0:
                    print "len(dbsApi.listDatasets(dataset = "+dset+")) > 0, exiting"
                    os.system('echo '+workflow+' | mail -s \"assignRelValWorkflow.py error 3\" andrew.m.levin@vanderbilt.edu --')
                    sys.exit(0)

                if "T2" in site:
                    site_disk = site
                elif "T1" in site:
                    site_disk = site + "_Disk"
                else:
                    os.system('echo '+site+' | mail -s \"assignRelValWorkflow.py error 4\" andrew.m.levin@vanderbilt.edu')
                    print "Neither T1 nor T2 is in site name, exiting"
                    sys.exit(1)

                if 'MCPileup' in value:
                    old_ld_library_path=os.environ['LD_LIBRARY_PATH']
                    os.environ['LD_LIBRARY_PATH']=''
                    isdatasetatsite=os.system("python2.6 check_if_dataset_is_at_a_site.py --dataset "+value['MCPileup']+" --site "+site_disk)
                    os.environ['LD_LIBRARY_PATH']=old_ld_library_path

                    if not isdatasetatsite:
                        print value['MCPileup']
                        os.system('echo '+workflow+' | mail -s \"assignRelValWorkflow.py error 6\" andrew.m.levin@vanderbilt.edu')
                        sys.exit(1)

                if 'InputDataset' in value:

                    subscribed_to_disk=False

                    inputdset=value['InputDataset']

                    if 'RunWhitelist' in value:
                        runwhitelist=value['RunWhitelist']
                        blocks=dbsApi.listBlocks(dataset = inputdset, run_num = runwhitelist)
                        for block in blocks:
                            
                            old_ld_library_path=os.environ['LD_LIBRARY_PATH']
                            os.environ['LD_LIBRARY_PATH']=''
                            isblockatsite=os.system("python2.6 check_if_block_is_at_a_site.py --block "+block['block_name']+" --site "+site_disk)
                            os.environ['LD_LIBRARY_PATH']=old_ld_library_path

                            #this block is not registered in phedex, so it cannot be subscribed to any site
                            if not isblockatsite and block['block_name'] != "/DoubleMu/Run2011A-ZMu-08Nov2011-v1/RAW-RECO#93c53d22-25b2-11e1-8c62-003048f02c8a":
                                os.system('echo '+workflow+' | mail -s \"assignRelValWorkflow.py error 5\" andrew.m.levin@vanderbilt.edu')
                                sys.exit(1)
                                
                            #print block['block_name']
                            #url=('https://cmsweb.cern.ch/phedex/datasvc/xml/prod/subscriptions?block='+block['block_name']).replace('#','%23')
                            #urlinput = urllib.urlopen(url)
                            #print url
                            #print urlinput
                            #xmldoc = minidom.parse(urlinput)
                            #for phedex in  xmldoc3.childNodes:
                            #    for dataset in phedex.childNodes:
                            #        for block in dataset.childNodes:
                            #            for subscription in block.childNodes:
                            #                if subscription.attributes['node'].value == site_disk:
                            #                    subscribed_to_disk=True
                            #print subscribed_to_disk            

    # Adding the "PU_" string into the ProcessingString value
    if options.pu:
        for key,value in procstring.items():
            if schema['Task1']['TaskName'] == 'ZmumuJets_Pt_20_300':
                continue
            if 'PU' not in value:
                procstring[key] = 'PU_'+value


    # Adding the special string - in case it was provided in the command line 
    if options.special:
        #specialStr = '_03Jan2013'
        specialStr = '_'+str(options.special)
        for key,value in procstring.items():
            procstring[key] = value+specialStr

    # Changing the team name and the site whitelist in case the --lsf parameter was given   
    if options.lsf:
        team='relvallsf'
        site='T2_CH_CERN'

    #maxrss=2972000
    maxrss=3072000
    #maxrss=3572000
    if options.high_memory:
        maxrss=4972000

    
    # If the --test argument was provided, then just print the information gathered so far and abort the assignment
    if options.test:
        print workflow, '\tAcqEra:', acqera, '\tProcStr:', procstring, '\tProcVer:', procversion, '\tTeam:',team, '\tSite:', site
        sys.exit(0);

    # Really assigning the workflow now
    print workflow, '\tAcqEra:', acqera, '\tProcStr:', procstring, '\tProcVer:', procversion, '\tTeam:',team, '\tSite:', site
    assignRequest(url,workflow,team,site,acqera,procstring,procversion,activity,lfn,maxrss)
    sys.exit(0);

if __name__ == "__main__":
    main()
