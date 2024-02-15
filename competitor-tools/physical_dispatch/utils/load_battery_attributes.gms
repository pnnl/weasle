* ESPA-Comp: Dispatch Data Loading Utility, Battery Attributes

Parameters
imax(n)         Maximum cell current charge into battery n   
imin(n)         Maximum cell current discharge from battery n
vmax(n)         Maximum cell voltage of battery n
vmin(n)         Minimum cell voltage of battery n
ch_cap(n)       Charge capacity of battery n
eff_coul(n)     Coulombic efficiency of battery n   Float   %
eff_inv0(n)     0-order inverter efficiency coefficient of battery n  
eff_inv1(n)     1st order inverter efficiency coefficient of battery n
eff_inv2(n)     2nd-ord inverter efficiency coefficient of battery n
voc0(n)         0th-order open-circuit voltage coefficient of battery n
voc1(n)         1st-order open-circuit voltage coefficient of battery n
voc2(n)         2nd-order open-circuit voltage coefficient of battery n
voc3(n)         3rd-order open-circuit voltage coefficient of battery n
chmax(n)        Maximum discharge power of battery n
dcmax(n)        Maximum charge power of battery n
pmin(n)         Minimum power output of battery n
pmax(n)         Maximum power output of battery n
cell_count(n)   Number of cells in battery n (power scaling factor)
resis(n)        Internal cell resistance of battery n    
* soc_init(n)     Initial state-of-charge of battery n (from load_previous_interval.gms)
socmax(n)       Maximum relative state-of-charge of battery n
socmin(n)       Minimum relative state-of-charge of battery n
socref(n)       Reference SoC of battery n
therm_cap(n)    Thermal capacity of battery n   
* temp_init(n)    Initial temperature of battery n (from load_previous_interval.gms)
temp_max(n)     Maximum cell temperature of battery n    
temp_min(n)     Minimum cell temperature of battery n    
temp_ref(n)     Reference cell temperature of battery n
Utherm(n)       Thermal transmittance between the surface of battery n and the environment
deg_DoD0(n)     0-order depth-of-discharge degradation coefficient of battery n
deg_DoD1(n)     1st-order depth-of-discharge degradation coefficient of battery n
deg_DoD2(n)     2nd-order depth-of-discharge degradation coefficient of battery n
deg_DoD3(n)     3rd-order depth-of-discharge degradation coefficient of battery n
deg_DoD4(n)     4th-order depth-of-discharge degradation coefficient of battery n
deg_soc(n)      State-of-charge degradation constant of battery n
deg_therm(n)    Thermal degradation constant of battery n
deg_time(n)     Time degradation constant of battery n  
cycle_life(n)   Rated cycle-life of battery n
cost_EoL(n)     End-of-Life cost of battery n
soc_capacity(n) Scaling factor for soc to convert MWh to percentages for battery n
;

* Load battery attribute data
$gdxin '%run_path%/data/storage_attributes.gdx'
$load resource, str
$load imax,imin,vmax,vmin,ch_cap,deg_DoD0,deg_DoD1,deg_DoD2,deg_DoD3,deg_DoD4
$load eff_coul,eff_inv0,eff_inv1,eff_inv2,deg_soc,deg_therm,deg_time,cycle_life
$load chmax,dcmax,resis,socmax,socmin,socref,voc0,voc1,voc2,voc3
$load therm_cap,temp_max,temp_min,temp_ref,Utherm,cost_Eol,soc_capacity,cell_count
$gdxin

* Scale pmin/max from MW to ~500kW cells. Scale soc to a percentage
pmin(n) = -chmax(n) * 1000 / cell_count(n);
pmax(n) = dcmax(n) * 1000 / cell_count(n);
socmax(n) = socmax(n) / soc_capacity(n);
socmin(n) = socmin(n) / soc_capacity(n);
socref(n) = socref(n) / soc_capacity(n);