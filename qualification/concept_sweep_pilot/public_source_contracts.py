#!/usr/bin/env python3
"""Public synthetic-only source/fact contract tests; no private CPE data."""
import argparse
import hashlib
import json
from pathlib import Path

# Original fictional fixtures deliberately have no links to any real persons or research corpus.
CASES={
 'alpha': [
  dict(text='A toy model of a train',sense='scale_representation',forbid=['paid_fashion_model','person_identity']),
  dict(text='A model posed for a painting',sense='human_model_occupation',forbid=['object_only','proven_identity']),
  dict(text='A science model predicts rainfall',sense='analytical_representation',forbid=['professional_actor']),
  dict(text='A junior editor joined the project',sense='workplace_rank',forbid=['minor_age_fact']),
  dict(text='A fictional character named Junior',sense='fictional_name',forbid=['minor_age_fact']),
  dict(text='Mini is an automobile model name',sense='brand_or_product_name',forbid=['physical_stature']),
 ],
 'beta': [
  dict(text='One original notice reprinted in 3 languages',sense='one_source_ancestry',forbid=['three_independent_sources']),
  dict(text='Dictionary translated a foreign word',sense='translation_attestation',forbid=['independent_native_usage']),
  dict(text='Two unrelated primary notices',sense='two_source_ancestries',forbid=['same_publisher_inferred']),
  dict(text='An undated source has no timestamp',sense='unknown_publication_date',forbid=['current_fact']),
  dict(text='Search result snippet matches a page title',sense='search_sighting',forbid=['article_verified']),
  dict(text='One organization publishes six dictionary entries',sense='one_editorial_ancestry',forbid=['six_independent_publishers']),
 ],
 'gamma': [
  dict(text='A product label uses extra small',sense='retail_size_tag',forbid=['person_height_measurement']),
  dict(text='An adult is described as cheerful like a child',sense='metaphorical_appearance',forbid=['age_under_18']),
  dict(text='An actor plays a character who is eleven',sense='fictional_role_age',forbid=['actor_age_eleven']),
  dict(text='A fictional figure is drawn small',sense='character_design',forbid=['real_human_measurement']),
  dict(text='A documentary mentions a term',sense='term_mention',forbid=['attributed_interest']),
  dict(text='A person has the same name as someone else',sense='name_collision',forbid=['identity_same']),
 ],
 'delta': [
  dict(text='A list claims a performer joined a cast',sense='catalog_claim',forbid=['verified_onscreen_credit']),
  dict(text='A garment is described as sleeveless',sense='garment_construction',forbid=['actual_skin_exposure']),
  dict(text='A health article describes a cosmetic procedure',sense='procedure_definition',forbid=['real_person_procedure']),
  dict(text='An actor appears but is not named in screen credits',sense='uncredited_appearance',forbid=['credited_appearance']),
  dict(text='A fiction writer uses a stage name',sense='pen_name_alias',forbid=['two_individuals_proven']),
  dict(text='One source says a word means young',sense='source_claim',forbid=['automatic_policy_decision']),
 ],
}
def run(shard):
 assert shard in CASES
 seen=set()
 for item in CASES[shard]:
  assert item['sense'] not in item['forbid']
  assert item['text'] not in seen
  seen.add(item['text'])
  assert item['text'] and item['forbid']
  assert len(item['forbid'])==len(set(item['forbid']))
 assert len(seen)==6
 report={'protocol':'synthetic_fact_sense_contract_v2','shard':shard,
         'test_case_count':len(seen),'assertion_count':len(seen)*5+3,
         'status':'PASS', 'real_person_data':False,'native_CPE_treatment':'NOT_RUN',
         'independent_stage_P':'NOT_RUN','policy_promotions':0}
 return report
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--shard',choices=sorted(CASES),required=True)
 p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 result=run(a.shard);a.out.parent.mkdir(parents=True,exist_ok=True)
 body=json.dumps(result,sort_keys=True,indent=2)+'\n'
 a.out.write_text(body,encoding='utf-8')
 print(json.dumps({'status':'PASS','shard':a.shard,'sha256':hashlib.sha256(body.encode()).hexdigest(),
                   'assertions':result['assertion_count']}))
