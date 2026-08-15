# Sunways Enhanced for Home Assistant

An enhanced fork of [adamus-tork/home-assistant-sunways](https://github.com/adamus-tork/home-assistant-sunways), using the cloud API at [sunways-portal.com](https://sunways-portal.com).

## Additional sensors

- Battery state of charge (SOC)
- Battery charging power
- Battery discharging power
- Battery energy-flow direction
- Grid energy-flow direction
- Load energy-flow direction
- Solar energy-flow direction
- EPS/backup energy-flow direction
- EPS/backup power
- Logger Wi-Fi signal (raw value because the portal does not specify `%` or `dBm`)
- Station status
- PV string 1/2 voltage and current
- Grid voltage and current for L1, L2 and L3
- Grid frequency
- EPS voltage, current and frequency for L1, L2 and L3
- Battery SOH, voltage and current
- Minimum and maximum battery cell voltage
- Battery charge and discharge current limits
- Inverter and battery temperature

The original solar, load, grid and generation sensors remain available.

Transient portal errors keep the last valid values. The integration only marks
the station unavailable after three consecutive overview failures, preventing
one-minute gaps without hiding a longer outage.

## HACS installation

1. Open HACS in Home Assistant.
2. Open the three-dot menu and select **Custom repositories**.
3. Add `https://github.com/alesjindrak/home-assistant-sunways-enhanced` as an **Integration**.
4. Install **Sunways Enhanced**.
5. Restart Home Assistant.

If the original Sunways integration is already installed, HACS will update the same `sunways` custom-component directory. Existing configuration entries and entity unique IDs are preserved.

## Compatibility

The extra sensors combine the station-overview response with the portal's detailed-device `queryRealTimeData` endpoint. The detailed endpoint returns a time series, so the integration uses the newest available value for each parameter. Missing optional fields return `unknown` instead of failing the whole integration. The first inverter returned for a station is currently used when a station contains multiple devices.

## Attribution

This project is based on the original Apache-2.0 licensed integration by Adamus Tork. See [LICENSE](LICENSE).

## Disclaimer

This project is not associated with or endorsed by Sunways. It uses an unofficial cloud API that may change without notice.
