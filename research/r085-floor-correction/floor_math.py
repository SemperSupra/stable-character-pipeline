"""R085 source-free deterministic bounded floor-only intervention."""
import math
MAX_ROOT_LIFT_M=.12
CONTACT_MARGIN_M=.003
def lift_for_min_z(z):
 if type(z) not in (int,float) or not math.isfinite(z):raise ValueError("NONFINITE_SOLE_HEIGHT")
 value=max(0.,-float(z)+CONTACT_MARGIN_M) if z<0 else 0.
 if value>MAX_ROOT_LIFT_M:raise ValueError("ROOT_LIFT_OVER_ENVELOPE")
 return round(value,8)
