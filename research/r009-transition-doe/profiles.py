"""Bounded original root-correction profile; analytic value and derivative per frame."""
KINDS=("linear","cubic","quintic")
HEIGHT=.03
CENTER=60
HALVES=(10,20)

def shape(kind,u):
    if kind=="linear":return u,1.
    if kind=="cubic":return u*u*(3-2*u),6*u*(1-u)
    if kind=="quintic":return u*u*u*(10+u*(-15+6*u)),30*u*u*(1-u)*(1-u)
    raise ValueError("PROFILE_KIND")

def point(kind,half,frame):
    if kind not in KINDS or type(half) is not int or half not in HALVES:
        raise ValueError("PROFILE_ADMISSION")
    offset=frame-CENTER
    if abs(offset)>=half:return 0.,0.
    u=1-abs(offset)/half
    val,derivative=shape(kind,u)
    direction=1 if offset<0 else -1 if offset>0 else 0
    return HEIGHT*val,HEIGHT*derivative*direction/half
