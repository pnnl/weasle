* ESPA-Comp: Dispatch Data Loading Utility, Previous Interval Data

Parameters
soc(n)          Interval-ending state-of-charge of battery n
temp(n)         Interval-ending cell temperature of battery n 
soc_init(n)     Recorded state-of-charge of battery n in interval t-1  
temp_init(n)    Recorded temperature of battery n in interval t-1      
;

* Load previous interval data
$gdxin '%run_path%/results/dispatch_%previous_uid%.gdx'
$load soc,temp
$gdxin

soc_init(n) = soc(n);
temp_init(n) = temp(n);