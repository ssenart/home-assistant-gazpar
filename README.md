# Home Assistant GrDF Gazpar

GrDF Gazpar integration permits to integrate in Home Assistant all your gas consumption data.

From version 1.2.0, it is compatible with [Lovelace Garpar Card](https://github.com/ssenart/lovelace-gazpar-card).

![Lovelace Garpar Card](images/gazpar-card.png)

GrDF Gazpar custom component is using [PyGazpar](https://github.com/ssenart/PyGazpar) library to retrieve GrDF data.

## Installation

### Method 1 : HACS (recommended)

Follow the steps described below to add GrDF Gazpar integration with [HACS](https://hacs.xyz/):

1. From [HACS](https://hacs.xyz/) (Home Assistant Community Store), open the upper left menu and select `Custom repositories` option to add the new repo.

2. Add the address <https://github.com/ssenart/home-assistant-gazpar> with the category `Integration`, and click `ADD`. The new corresponding repo appears in the repo list.

3. Select this repo (this integration description is displayed in a window) and click on `INSTALL THIS REPOSITORY` button on the lower right of this window.

4. Keep the last version and click the button `INSTALL` on the lower right.

5. Do click on `RELOAD` button for completion! The integration is now ready. It remains the configuration.

### Method 2 : Manual

Copy the gazpar directory in HA config/custom_components/gazpar directory.

## Configuration

Add to your Home Assistant configuration.yaml:

```yaml
sensor:
- platform: 'gazpar'
  name: 'gazpar'
  username: '***'
  password: '***'
  pce_identifier: 'xxxxxxxxx'
  tmpdir: '/tmp'
  scan_interval: '08:00:00'
  lastNDays: 365
```

'name' is the sensor name (only available from version 1.3.5-alpha.1). Its default value is 'gazpar'.

'lastNDays' is the number of days of data to download from GrDF (only available from version 1.3.9). Its default value is 1095 (3 years).

If you have the error: 
```
An error occurred while loading data. Status code: 500 - {"code":500,"message":"Internal Server Error"}
```
...it is likely you try to get more data than available. Please reduce the lastNDays parameter accordingly (see issue [#62](https://github.com/ssenart/home-assistant-gazpar/issues/62)).

Do not use special characters in your password.

Ensure that tmpdir already exists before starting HA. It is used to store the downloaded Excel files from GrDF.

If using multiple accounts, you can specify them with the following syntax:

```yaml
sensor:
- platform: 'gazpar'
  name: 'mygazpar'
  username: '***'
  password: '***'
  pce_identifier: 'xxxxxxxxx'
  tmpdir: '/tmp'
  scan_interval: '08:00:00'

- platform: 'gazpar'
  name: 'othergazpar'
  username: '***'
  password: '***'
  pce_identifier: 'xxxxxxxxx'
  tmpdir: '/tmp'
  scan_interval: '08:00:00'  
```

Restart your HA application. In HA development panel, you should see the new Gazpar entity 'sensor.gazpar' with its corresponding attributes:

- sensor.gazpar:
```yaml
attribution: Data provided by GrDF
username: titi.toto@tata.fr
pce: 123456789
unit_of_measurement: kWh
friendly_name: Gazpar
icon: mdi:fire
device_class: energy
state_class: total_increasing
errorMessages:
hourly: 
daily: 
- time_period: 07/10/2022
  start_index_m3: 15714
  end_index_m3: 15716
  volume_m3: 2
  energy_kwh: 21
  converter_factor_kwh/m3: 11.27
  type: Mesuré
  timestamp: '2022-10-09T20:59:12.356210'
- time_period: 06/10/2022
  start_index_m3: 15713
  end_index_m3: 15714
  volume_m3: 2
  energy_kwh: 17
  converter_factor_kwh/m3: 11.27
  type: Mesuré
  timestamp: '2022-10-09T20:59:12.356210'
...

weekly: 
- time_period: Du 03/10/2022 au 09/10/2022
  volume_m3: 9
  energy_kwh: 87
  timestamp: '2022-10-09T20:59:13.391911'
- time_period: Du 26/09/2022 au 02/10/2022
  volume_m3: 11
  energy_kwh: 132
  timestamp: '2022-10-09T20:59:13.391911'
...

monthly: 
- time_period: 'Octobre 2022 '
  volume_m3: 12
  energy_kwh: 119
  timestamp: '2022-10-09T20:59:14.447149'
- time_period: 'Septembre 2022 '
  volume_m3: 34
  energy_kwh: 409
  timestamp: '2022-10-09T20:59:14.447149'
...

yearly: 
- time_period: '2022'
  energy_kwh: 11958
  volume_m3: 1078
- time_period: '2021'
  energy_kwh: 23148
  volume_m3: 2099
- time_period: '2020'
  energy_kwh: 21160
  volume_m3: 1904

...
```

## Home Assistant Energy module integration

### Gazpar2HAWS

A new application [Gazpar2HAWS](https://github.com/ssenart/gazpar2haws) has been developed to feed the Home Assistant Energy dashboard.

It is able to rebuild the full data history and keep it updated.

The dates are now in sync with Home Assistant.

### Legacy method

You probably want to integrate GrDF data into the Home Assistant Energy module.

![Dashboard](images/energy_module.png)

In Home Assistant energy configuration panel, you can set directly the sensor 'sensor.gazpar' in the gas consumption section.

I prefer using an alias for all my sensors so I keep control on the sensor naming. For that, I define a template and use the template sensor.gas_energy to configure the dashboard.

```yaml
- sensor:
  - name: gas_energy
    unit_of_measurement: 'kWh'      
    state: >
      {{ states('sensor.gazpar') }}
    icon: mdi:fire
    device_class: energy
    state_class: total_increasing
```

For those who prefer to use the volume data instead of the energy (kWh) data, the following template can also be used:

```yaml
- sensor:
  - name: gas_volume
    unit_of_measurement: 'm³'
    state: >
      {{ state_attr('sensor.gazpar', 'daily')[0]['start_index_m3'] + state_attr('sensor.gazpar', 'daily')[0]['volume_
m3']}}
    icon: mdi:fire
    device_class: gas
    state_class: total_increasing
```
