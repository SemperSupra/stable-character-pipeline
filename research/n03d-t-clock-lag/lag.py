"""Select BVH-to-retarget clock offset exclusively by train root error."""
from planar import fit,transform,error
def qualify(source,target,train_start=12,train_end=70,test_start=71,test_end=130,lag_limit=12):
 if len(source)!=len(target) or len(source)!=143:raise ValueError("SOURCE_SAMPLE_CLOCK")
 if not (0<=train_start<train_end<test_start<=test_end<143):raise ValueError("LEAKED_TRAIN_TEST")
 if not 1<=lag_limit<=12:raise ValueError("LAG_BOUND")
 results=[]
 for lag in range(-lag_limit,lag_limit+1):
  a=source[train_start+lag:train_end+lag+1]
  b=target[train_start:train_end+1]
  model=fit(a,b)
  train_err=error(transform(model,a),b)
  test_err=error(transform(model,source[test_start+lag:test_end+lag+1]),
       target[test_start:test_end+1])
  results.append({"lag_samples":lag,"lag_seconds":round(lag/24,9),
    "train_root_rmse_m":train_err,"heldout_root_rmse_m":test_err,
    "calibrated_scale":round(model["scale"],8),
    "calibrated_yaw_rad":round(__import__("math").atan2(model["sin"],model["cos"]),6)})
 selected=min(results,key=lambda x:(x["train_root_rmse_m"],abs(x["lag_samples"]),x["lag_samples"]))
 baseline=next(x for x in results if x["lag_samples"]==0)
 return {"all_lags":results,"selected_by":"TRAIN_RMSE_ONLY_NOT_HELDOUT",
  "best_train_lag":selected,"zero_lag_baseline":baseline,
  "heldout_result_was_not_used_to_choose_lag":True,
  "root_timebase_physical_accuracy_accepted":False}
