#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import requests
import subprocess
from collections import Counter
import sys

## this script finds the peeringLANs that RIS is at, shows the number of potential peers (per peeringDB data)
# and if we'd want to be able to reach new peers 

## whois -h riswhois.ripe.net peers | egrep -v '^%' | perl -lane' $c{ $F[1] }=1; END { print scalar keys %c }'
## 536
ris_asn_set = set()
rw_output=subprocess.check_output("whois -h riswhois.ripe.net peers", shell=True, text=True)
for line in rw_output.split('\n'):
    if line.startswith('rrc'):
        fields = line.split()
        rrc=fields[0]
        asn=fields[1]
        ris_asn_set.add( asn ) # maybe do same for the full-table set?
        v4routes=fields[3]
        v6routes=fields[4]

r = requests.get(f'https://www.peeringdb.com/api/net?asn__in={",".join(list(ris_asn_set))}')
j = r.json()
ris_asn_type_c = Counter()
ris_asn_traffic_c = Counter()
for asn in j['data']:
    ris_asn_type_c[ asn['info_type'] ] += 1
    ris_asn_traffic_c[ asn['info_traffic'] ] += 1

'''
cs = sum(ris_asn_type_c.values())
ris_asn_type_c['not_in_peeringdb'] = len( ris_asn_set ) - cs
for k,v in ris_asn_type_c.most_common():
    print(f"{100.0*v/cs}\t{k}")

cs = sum(ris_asn_traffic_c.values())
ris_asn_traffic_c['not_in_peeringdb'] = len( ris_asn_set ) - cs
for k,v in ris_asn_traffic_c.most_common():
    print(f"{100.0*v/cs}\t{k}")
'''

'''
{'id': 21544, 'org_id': 24469, 'name': 'SA Domain Internet Services', 'aka': 'SA Domain', 'name_long': 'SA Domain Fibre', 'website': 'https://www.sadomain.co.za', 'asn': 328575, 'looking_glass': '', 'route_server': '', 'irr_as_set': 'AS-SET-AS328575', 'info_type': 'Cable/DSL/ISP', 'info_prefixes4': 10, 'info_prefixes6': 5, 'info_traffic': '', 'info_ratio': 'Not Disclosed', 'info_scope': '', 'info_unicast': True, 'info_multicast': False, 'info_ipv6': True, 'info_never_via_route_servers': False, 'ix_count': 2, 'fac_count': 2, 'notes': '', 'netixlan_updated': '2021-09-22T00:08:26.443082Z', 'netfac_updated': '2021-06-11T16:23:41.032379Z', 'poc_updated': '2020-05-19T22:27:28Z', 'policy_url': '', 'policy_general': 'Open', 'policy_locations': 'Not Required', 'policy_ratio': False, 'policy_contracts': 'Not Required', 'allow_ixp_update': True, 'created': '2019-11-27T09:29:17Z', 'updated': '2021-05-11T17:12:27Z', 'status': 'ok'}
'''

## fetch RIS pdb entry
## RIS ASNS
## doesn't work
r = requests.get("https://www.peeringdb.com/api/net?asn=12654&depth=2")
j = r.json()
if len( j['data'] ) != 1:
    print("## number of RIS instances in peeringDB != 1. EEPS")
    exit( 1 )
ris_ixlan_ids = list( map( lambda x: x['ixlan_id'], j['data'][0]['netixlan_set'] ) )
#print( ris_ixlan_ids )

### fetch the LANs that RIS is at
ris_ixlan_set = set( ris_ixlan_ids )
reachable_asns = set()
r = requests.get("https://www.peeringdb.com/api/ixlan?id__in={}&depth=2".format( ",".join( map( str, ris_ixlan_ids ) ) ) )
j = r.json()
for ixlan in j['data']:
    for net in ixlan['net_set']:
        a = net['asn']
        reachable_asns.add( a )

'''
### what do the reachable asns look like?
def batch(iterable, n=1):
    l = len(iterable)
    for ndx in range(0, l, n):
        yield iterable[ndx:min(ndx + n, l)]

print(f"reachable ASN: {len( reachable_asns) }")
ris_reach_asn_type_c = Counter()
for b in batch( list(reachable_asns), 500 ):
    reachable_url=f'https://www.peeringdb.com/api/net?asn__in={",".join(map( str, b))}'
    r = requests.get( reachable_url )
    j = r.json()
    for asn in j['data']:
        ris_reach_asn_type_c[ asn['info_type'] ] += 1

print( ris_reach_asn_type_c )
cs = sum(ris_reach_asn_type_c.values())
for k,v in ris_reach_asn_type_c.most_common():
    print(f"{100.0*v/cs}\t{k}")
'''


r = requests.get("https://www.peeringdb.com/api/ixlan?&depth=2")
j = r.json()
lans = []
for ixlan in j['data']:
    if ixlan['id'] in ris_ixlan_set:
        continue
    this_lan_new = set() #new for ris 
    this_lan_cov = set() #covered for ris
    for net in ixlan['net_set']:
        a = net['asn']
        if a in reachable_asns:
            this_lan_cov.add( a )
        else:
            this_lan_new.add( a )
    lans.append(
        {'id': ixlan['id'],
         'ix_id': ixlan['ix_id'],
         'new': this_lan_new,
         'cov': this_lan_cov
        }
    )

lans.sort(key=lambda x: len( x['new'] ))

for lan in lans[-100:]:
    r = requests.get(f"https://www.peeringdb.com/api/ix?id={lan['ix_id']}")
    j = r.json()

    i = j['data'][0]
    print(f"new ASNs:{len(lan['new'])} ix_id:{i['id']} name:{i['name']} city:{i['city']} country:{i['country']}")
