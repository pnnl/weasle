* ESPA-Comp: Dispatch Data Loading Utility, Current Interval Data

Parameters
target(n)       Desired dispatch level of battery n in interval t
temp_env(n)     Ambient temperature in interval t
duration_t      Duration of the cleared interval in minutes
duration_s      Duration of the cleared interval in seconds
duration_h      Duration of the cleared interval in hours
;

* Load current interval data
$gdxin '%run_path%/data/target_%market_uid%.gdx'
$load target,temp_env
$load duration_t
$gdxin

duration_s = duration_t * 60;
duration_h = duration_t / 60;