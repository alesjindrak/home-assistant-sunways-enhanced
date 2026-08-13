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

The original solar, load, grid and generation sensors remain available.

## HACS installation

1. Open HACS in Home Assistant.
2. Open the three-dot menu and select **Custom repositories**.
3. Add `https://github.com/alesjindrak/home-assistant-sunways-enhanced` as an **Integration**.
4. Install **Sunways Enhanced**.
5. Restart Home Assistant.

If the original Sunways integration is already installed, HACS will update the same `sunways` custom-component directory. Existing configuration entries and entity unique IDs are preserved.

## Compatibility

The extra sensors are based on fields observed in the station-overview response. Missing optional fields return `unknown` instead of failing the whole integration. Detailed battery voltage, current, SOH, temperature and per-string PV data are not supplied by this overview endpoint and require a future detailed-device API implementation.

## Attribution

This project is based on the original Apache-2.0 licensed integration by Adamus Tork. See [LICENSE](LICENSE).

## Disclaimer

This project is not associated with or endorsed by Sunways. It uses an unofficial cloud API that may change without notice.
