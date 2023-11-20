import asyncio
import logging
import json
import time
from datetime import datetime
from bleuio_lib.bleuio_funcs import BleuIO


my_dongle = None


def my_scan_callback(scan_input):
    global mydata
    mydata = scan_input


def convertNumber(data, start, end):
    pos = data.find("5B070")
    return int.from_bytes(
        bytes.fromhex(data[pos + start : pos + start + end])[::-1], byteorder="big"
    )


def adv_data_decode(data):
    pos = data.find("5B070")
    dt = datetime.now()
    current_ts = dt.strftime("%Y/%m/%d %H:%M:%S")
    temp_hex = convertNumber(data, 22, 4)
    if temp_hex > 1000:
        temp_hex = (temp_hex - (65535 + 1)) / 10
    else:
        temp_hex = temp_hex / 10

    env_data = {
        "boardID": data[pos + 8 : pos + 8 + 6],
        "type": int(data[pos + 6 : pos + 6 + 2], 16),
        "light": convertNumber(data, 14, 4),
        "pressure": convertNumber(data, 18, 4) / 10,
        "temp": temp_hex,
        "hum": convertNumber(data, 26, 4) / 10,
        "voc": convertNumber(data, 30, 4),
        "pm1": convertNumber(data, 34, 4) / 10,
        "pm25": convertNumber(data, 38, 4) / 10,
        "pm10": convertNumber(data, 42, 4) / 10,
        "co2": int(data[pos + 46 : pos + 46 + 4], 16),
        "vocType": int(data[pos + 50 : pos + 50 + 2], 16),
        "ts": current_ts,
    }

    return env_data


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the Snoopinator BLE platform."""
    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="Snoopinator BLE Sensor",
        update_method=async_update_data,
    )

    await coordinator.async_refresh()

    async_add_entities(
        [
            SnoopinatorBLESensor(
                coordinator, "temperature", "Temperature", "°C", "mdi:thermometer"
            ),
            SnoopinatorBLESensor(
                coordinator, "humidity", "Humidity", "%rH", "mdi:water-percent"
            ),
            SnoopinatorBLESensor(coordinator, "pm1", "PM1", "µg/m³", "mdi:blur"),
            SnoopinatorBLESensor(coordinator, "pm25", "PM2.5", "µg/m³", "mdi:blur"),
            SnoopinatorBLESensor(coordinator, "pm10", "PM10", "µg/m³", "mdi:blur"),
            SnoopinatorBLESensor(coordinator, "voc", "VOC", "ppm", "mdi:cloud"),
            SnoopinatorBLESensor(coordinator, "co2", "CO2", "ppm", "mdi:molecule-co2"),
            SnoopinatorBLESensor(coordinator, "pressure", "Pressure", "mbar", "mdi:gauge"),
            SnoopinatorBLESensor(
                coordinator, "ts", "Last updated", "", "mdi:calendar-clock"
            ),
            SnoopinatorBLESensor(coordinator, "als", "Light", "lux", "mdi:brightness-7"),
        ]
    )


async def async_update_data():
    """Fetch data from your data source and return it."""
    global my_dongle
    if my_dongle is None:
        my_dongle = BleuIO()
        my_dongle.register_scan_cb(my_scan_callback)
        my_dongle.at_dual()
    try:
        my_dongle.at_findscandata(DEVICEID, 3)
        time.sleep(3)
        data_list = json.loads(mydata[0])
        _LOGGER.error(str(data_list["data"]))
        parsed_data = adv_data_decode(str(data_list["data"]))
        my_dongle.stop_scan()
        temperature = parsed_data.get("temp")
        humidity = parsed_data.get("hum")
        pm1 = parsed_data.get("pm1")
        pm25 = parsed_data.get("pm25")
        pm10 = parsed_data.get("pm10")
        voc = parsed_data.get("voc")
        co2 = parsed_data.get("co2")
        pressure = parsed_data.get("pressure")
        als = parsed_data.get("light")
        ts = parsed_data.get("ts")
        _LOGGER.error(parsed_data)

        return {
            "temperature": temperature,
            "humidity": humidity,
            "pm1": pm1,
            "pm25": pm25,
            "pm10": pm10,
            "voc": voc,
            "co2": co2,
            "als": als,
            "pressure": pressure,
            "ts": ts,
        }

    except Exception as e:
        _LOGGER.error("Error updating Snoopinator BLE sensor: %s", e)


class SnoopinatorBLESensor(Entity):
    """Representation of a Snoopinator BLE sensor."""

    def __init__(self, coordinator, sensor_type, sensor_name, unit, icon):
        """Initialize the sensor."""
        self._coordinator = coordinator
        self._sensor_type = sensor_type
        self._sensor_name = sensor_name
        self._unit = unit
        self._icon = icon

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"Snoopinator-BLE {self._sensor_name}"

    @property
    def state(self):
        """Return the state of the sensor."""
        data = self._coordinator.data
        return data.get(self._sensor_type)

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return self._unit

    @property
    def icon(self):
        """Return the icon to be displayed for this entity."""
        return self._icon

    async def async_update(self):
        """Update the sensor."""
        await self._coordinator.async_request_refresh()