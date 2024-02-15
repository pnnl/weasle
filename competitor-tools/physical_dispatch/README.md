# Physical Dispatch Models

# data
The _data_ folder contains a json file with the standard battery attributes assigned to each storage device.

# storage
The _storage_ folder contains two scripts that are used to calculate battery dispatch and degradation, respectively.

`battery_degradation.py` is used to calculate degradation. Users can provide a sample array of battery state-of-charge
status and temperature, and the script will calculate the estimated degradation cost.

`battery_dispatch.gms` is provided for informational purposes. Users may need to modify the code to simulate effects of 
various battery dispatch decisions on state-of-charge and temperature.

`utils` includes various GAMS scripts for loading input data into `battery_dispatch.gms`. 