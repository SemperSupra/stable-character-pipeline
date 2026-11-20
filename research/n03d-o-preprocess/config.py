SETTINGS={'auto_normalized':(True,True),'fixed_normalized':(False,True),'auto_unmodified':(True,False),'fixed_unmodified':(False,False)}
def variant_settings(name):
 if name not in SETTINGS:raise ValueError('BAD_PREPROCESSING_VARIANT')
 a,n=SETTINGS[name]
 return {'useAutoScale':a,'useNormalizeSource':n}
