#### Init
service_domain = data.get('service_domain')
service = data.get('service')
service_data_increase = dict(data.get('service_data_increase') or {})
service_data_decrease = dict(data.get('service_data_decrease') or {})

target_percentage = data.get('fan_speed')
speed_count = data.get('fan_speed_count')
fan_speed_entity_id = data.get('fan_speed_entity_id')
fan_entity_id = data.get('fan_entity_id')

command_delay = data.get('command_delay', 1.0)
startup_delay = data.get('startup_delay', 1.0)
power_on_percentage = data.get('power_on_percentage')
wrap_increase = data.get('wrap_increase', False)
wrap_decrease = data.get('wrap_decrease', False)
support_num_repeats = data.get('support_num_repeats', False)

fan_speed_entity = hass.states.get(fan_speed_entity_id) if fan_speed_entity_id else None
fan_entity = hass.states.get(fan_entity_id) if fan_entity_id else None


def clamp(value, minimum, maximum):
  if value < minimum:
    return minimum
  if value > maximum:
    return maximum
  return value


def as_float(value, default, label, minimum=None):
  try:
    parsed = float(value)
  except (TypeError, ValueError):
    logger.warning('<fan_speed_control> {} ({}) is invalid, fallback to {}'.format(label, value, default))
    return default

  if minimum is not None and parsed < minimum:
    logger.warning('<fan_speed_control> {} ({}) must be >= {}, fallback to {}'.format(label, value, minimum, default))
    return default

  return parsed


def as_int(value, default, label, minimum=None, maximum=None):
  try:
    parsed = int(float(value))
  except (TypeError, ValueError):
    logger.warning('<fan_speed_control> {} ({}) is invalid, fallback to {}'.format(label, value, default))
    return default

  if minimum is not None and parsed < minimum:
    logger.warning('<fan_speed_control> {} ({}) must be >= {}, fallback to {}'.format(label, value, minimum, default))
    return default

  if maximum is not None and parsed > maximum:
    logger.warning('<fan_speed_control> {} ({}) must be <= {}, fallback to {}'.format(label, value, maximum, default))
    return default

  return parsed


def as_bool(value):
  if value is True:
    return True
  if value is False or value is None:
    return False
  return str(value).lower() in ('1', 'true', 'yes', 'on')


def percentage_to_step(percentage, speed_max):
  if percentage <= 0:
    return 0

  step = int(round((float(percentage) * speed_max) / 100.0))
  return clamp(step, 1, speed_max)


def step_to_percentage(step, speed_max):
  if step <= 0:
    return 0

  percentage = int(round((float(step) * 100.0) / speed_max))
  return clamp(percentage, 1, 100)


def sync_speed_helper(percentage):
  hass.services.call('input_number', 'set_value', {
    'entity_id': fan_speed_entity_id,
    'value': percentage
  })


def send_control(payload):
  logger.debug('<fan_speed_control> call service ({}.{}) {}'.format(service_domain, service, payload))
  hass.services.call(service_domain, service, payload)


def send_repeated(payload, count, delay_seconds):
  if count <= 0:
    return

  if support_num_repeats:
    repeated_payload = dict(payload)
    repeated_payload['num_repeats'] = count
    repeated_payload['delay_secs'] = delay_seconds
    send_control(repeated_payload)
    return

  for index in range(count):
    send_control(dict(payload))
    if index + 1 < count and delay_seconds > 0:
      time.sleep(delay_seconds)


def choose_direction(current_step, requested_step, speed_max, allow_wrap_increase, allow_wrap_decrease):
  if requested_step == current_step:
    return None, 0

  if requested_step > current_step:
    best_direction = 'increase'
    best_count = requested_step - current_step

    if allow_wrap_decrease:
      wrap_count = current_step + speed_max - requested_step
      if wrap_count < best_count:
        best_direction = 'decrease'
        best_count = wrap_count

    return best_direction, best_count

  best_direction = 'decrease'
  best_count = current_step - requested_step

  if allow_wrap_increase:
    wrap_count = requested_step + speed_max - current_step
    if wrap_count < best_count:
      best_direction = 'increase'
      best_count = wrap_count

  return best_direction, best_count


def get_current_percentage(default_percentage):
  if fan_speed_entity is None or fan_speed_entity.state in ('unknown', 'unavailable', None, ''):
    logger.warning('<fan_speed_control> fan speed helper is invalid, fallback to {}'.format(default_percentage))
    return default_percentage

  current_percentage = as_int(fan_speed_entity.state, default_percentage, 'fan_speed_entity_id state')
  return clamp(current_percentage, 0, 100)


def turn_on_fan():
  logger.debug('<fan_speed_control> call fan.turn_on')
  hass.services.call('fan', 'turn_on', {
    'entity_id': fan_entity_id
  })


def turn_off_fan():
  logger.debug('<fan_speed_control> call fan.turn_off')
  hass.services.call('fan', 'turn_off', {
    'entity_id': fan_entity_id
  })


def missing_required_config():
  return not fan_entity_id or not fan_speed_entity_id or not service_domain or not service


if missing_required_config():
  logger.warning('<fan_speed_control> missing required configuration')
elif fan_entity is None:
  logger.warning('<fan_speed_control> fan entity is missing')
elif fan_speed_entity is None:
  logger.warning('<fan_speed_control> fan speed helper entity is missing')
else:
  speed_count = as_int(speed_count, 0, 'fan_speed_count', minimum=1)
  if speed_count <= 0:
    logger.warning('<fan_speed_control> fan_speed_count must be >= 1')
  else:
    command_delay = as_float(command_delay, 1.0, 'command_delay', minimum=0.0)
    startup_delay = as_float(startup_delay, 1.0, 'startup_delay', minimum=0.0)
    wrap_increase = as_bool(wrap_increase)
    wrap_decrease = as_bool(wrap_decrease)

    minimum_percentage = step_to_percentage(1, speed_count)
    default_power_on_percentage = minimum_percentage
    power_on_percentage = as_int(
      power_on_percentage if power_on_percentage is not None else default_power_on_percentage,
      default_power_on_percentage,
      'power_on_percentage',
      minimum=minimum_percentage,
      maximum=100
    )

    target_percentage = as_int(target_percentage, 0, 'fan_speed')
    target_percentage = clamp(target_percentage, 0, 100)
    target_step = percentage_to_step(target_percentage, speed_count)

    logger.debug('<fan_speed_control> fan state ({})'.format(fan_entity.state))
    logger.debug('<fan_speed_control> received fan speed target ({}) -> step ({})'.format(target_percentage, target_step))

    if target_step == 0:
      if fan_entity.state != 'off':
        turn_off_fan()
      else:
        logger.debug('<fan_speed_control> fan already off')
    else:
      current_percentage = get_current_percentage(power_on_percentage)
      current_step = percentage_to_step(current_percentage, speed_count)

      if fan_entity.state == 'off':
        logger.debug('<fan_speed_control> fan is off, assume startup speed ({})'.format(power_on_percentage))
        sync_speed_helper(power_on_percentage)
        turn_on_fan()
        if startup_delay > 0:
          time.sleep(startup_delay)
        current_percentage = power_on_percentage
        current_step = percentage_to_step(current_percentage, speed_count)

      if current_step == 0:
        logger.warning('<fan_speed_control> fan is on but helper speed is 0, assume minimum speed')
        current_step = 1

      direction, command_count = choose_direction(
        current_step,
        target_step,
        speed_count,
        wrap_increase,
        wrap_decrease
      )

      if direction == 'increase':
        send_repeated(service_data_increase, command_count, command_delay)
      elif direction == 'decrease':
        send_repeated(service_data_decrease, command_count, command_delay)
      else:
        logger.debug('<fan_speed_control> target speed already matches current speed')

      sync_speed_helper(step_to_percentage(target_step, speed_count))
