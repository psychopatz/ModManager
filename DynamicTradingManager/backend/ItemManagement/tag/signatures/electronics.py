"""
Electronics property-based signatures.
Detects electronic items through radio/light properties, power requirements,
and targeted ID patterns.
"""
from .helpers import (
    has_property,
    id_matches_pattern,
    PropertyAnalyzer,
    get_display_category,
    extract_tags_from_props,
)


ELECTRONICS_ID_PATTERNS = [
    'Radio', 'Walkie', 'Walkie Talkie', 'Generator', 'Battery', 'Electronic',
    'TV', 'Television', 'Computer', 'PC', 'Phone', 'Telephone', 'Camera',
    'Flashlight', 'PenLight', 'HandTorch', 'LightBulb', 'Alarm', 'Clock'
]

BATTERY_PATTERNS = ['Battery', 'Cell']
GENERATOR_PATTERNS = ['Generator', 'Solar']
COMMUNICATION_PATTERNS = ['Radio', 'Walkie', 'Phone', 'CB']
LIGHT_TAG_PATTERNS = ['base:flashlight', 'base:litlantern', 'base:unlitlantern']
LIGHT_COMPONENT_PATTERNS = ['LightBulb', 'Bulb']
NON_ELECTRONIC_LIGHT_DISPLAY_CATS = {'firesource', 'paint', 'junk', 'tool'}
EXCLUDED_LIGHT_ITEM_IDS = {
    'candle', 'candlelit',
    'lighter', 'lighterbbq', 'lighterdisposable', 'lighterfluid',
    'propane_refill',
}
ELECTRONIC_AUDIO_PATTERNS = ['Amplifier', 'Earbud', 'Headphone', 'Speaker', 'Microphone', 'VideoGame']
ELECTRONIC_CONTROL_PATTERNS = ['Remote', 'Timer', 'Trigger', 'MotionSensor', 'HomeAlarm', 'Scanner', 'PowerBar']
ELECTRONIC_COMM_PATTERNS = ['Phone', 'Pager', 'Receiver']
ELECTRONIC_GENERAL_TAGS = {'base:miscelectronic', 'base:tvremote', 'base:generator'}


def _extract_electronics_context(item_id, props, analyzer):
    """Extract the vanilla properties that strongly identify electronic items."""
    display_category = (get_display_category(props) or '').strip()
    display_category_lower = display_category.lower()
    tags = [tag.lower() for tag in extract_tags_from_props(props)]
    item_id_lower = item_id.lower()
    is_excluded_light_item = item_id_lower in EXCLUDED_LIGHT_ITEM_IDS

    transmit_range = analyzer.get_stat('TransmitRange')
    mic_range = analyzer.get_stat('MicRange')
    light_distance = analyzer.get_stat('LightDistance')
    light_strength = analyzer.get_stat('LightStrength')
    is_moveable = item_id.startswith('Mov_') or item_id.startswith('Move_')
    is_flashlight_like_id = (
        item_id in {'Torch', 'PenLight', 'HandTorch'} or
        id_matches_pattern(item_id, ['FlashLight', 'Flashlight'])
    )
    is_lantern_like_id = id_matches_pattern(item_id, ['Lantern'])
    has_light_tags = any(tag in tags for tag in LIGHT_TAG_PATTERNS)
    has_light_behavior = (
        has_property('TorchCone', props) or
        has_property('KeepOnDeplete', props) or
        has_property('ReplaceOnExtinguish', props) or
        has_property('DoubleClickRecipe', props)
    )

    is_radio_item = (
        has_property('ItemType', props, 'base:radio') or
        display_category_lower == 'communications'
    )
    is_general_electronics = (
        not is_moveable and
        display_category_lower == 'electronics'
    )
    is_light_source = (
        not is_moveable and
        display_category_lower == 'lightsource' and
        display_category_lower not in NON_ELECTRONIC_LIGHT_DISPLAY_CATS and
        (
            is_flashlight_like_id or
            is_lantern_like_id or
            has_light_tags or
            has_light_behavior
        )
    )
    is_light_component = (
        not is_moveable and
        display_category_lower == 'electronics' and
        id_matches_pattern(item_id, LIGHT_COMPONENT_PATTERNS)
    )

    return {
        'display_category': display_category,
        'display_category_lower': display_category_lower,
        'item_id_lower': item_id_lower,
        'tags': tags,
        'transmit_range': transmit_range,
        'mic_range': mic_range,
        'light_distance': light_distance,
        'light_strength': light_strength,
        'is_radio_item': is_radio_item,
        'is_general_electronics': is_general_electronics,
        'is_light_source': is_light_source,
        'is_light_component': is_light_component,
        'is_moveable': is_moveable,
        'is_excluded_light_item': is_excluded_light_item,
        'uses_battery': has_property('UsesBattery', props, 'true'),
        'requires_power': (
            has_property('BatteryMod', props) or
            has_property('RequiresElectricity', props)
        ),
        'is_portable': has_property('IsPortable', props, 'true'),
        'is_two_way': (
            has_property('TwoWay', props, 'true') or
            (transmit_range > 0 and mic_range > 0)
        ),
        'is_television': has_property('IsTelevision', props, 'true'),
        'has_signal': (
            transmit_range > 0 or
            mic_range > 0 or
            has_property('SignalStrength', props) or
            has_property('Transmitter', props)
        ),
    }


def matches_electronics_signature(item_id, props):
    """
    Check if item matches electronics signature.
    
    Electronics have:
    - Battery-related properties or IDs
    - Power/signal-related functionality
    - Electronic device ID patterns
    
    Args:
        item_id: Item identifier
        props: Properties string
    
    Returns:
        tuple: (matches: bool, confidence: float, details: dict)
    """
    analyzer = PropertyAnalyzer(props)
    
    context = _extract_electronics_context(item_id, props, analyzer)

    # Property-first detection for radios and light sources; ID patterns remain
    # as a fallback for more generic electronics like batteries and generators.
    is_electronics_id = id_matches_pattern(item_id, ELECTRONICS_ID_PATTERNS)
    if context['is_moveable']:
        return False, 0.0, {}

    if context['is_excluded_light_item']:
        return False, 0.0, {}

    if has_property('Trap', props, 'true') or context['display_category_lower'] == 'trapping':
        return False, 0.0, {}

    if not (
        context['is_radio_item'] or
        context['is_general_electronics'] or
        context['is_light_source'] or
        context['is_light_component'] or
        is_electronics_id
    ):
        return False, 0.0, {}

    evidence = []
    details = {
        'electronics_type': 'General',
        'is_battery': False,
        'is_generator': False,
        'is_communication': False,
        'display_category': context['display_category'],
        'is_portable': context['is_portable'],
        'uses_battery': context['uses_battery'],
    }

    if context['is_radio_item']:
        evidence.append(0.55)
        details['is_communication'] = True
        details['has_signal'] = context['has_signal']
        details['is_two_way'] = context['is_two_way']
        details['transmit_range'] = context['transmit_range']
        details['mic_range'] = context['mic_range']

        if context['is_television']:
            details['electronics_type'] = 'Television'
            evidence.append(0.15)
        elif context['is_two_way']:
            if id_matches_pattern(item_id, ['Walkie']):
                details['electronics_type'] = 'Radio.TwoWay.Walkie'
            elif id_matches_pattern(item_id, ['Ham', 'ManPack']) or not context['is_portable']:
                details['electronics_type'] = 'Radio.TwoWay.Ham'
            else:
                details['electronics_type'] = 'Radio.TwoWay.Portable'
            evidence.append(0.25)
        else:
            details['electronics_type'] = 'Radio.Broadcast'
            evidence.append(0.2)

        if context['uses_battery']:
            evidence.append(0.1)
        if context['is_portable']:
            evidence.append(0.05)
        if context['has_signal']:
            evidence.append(0.1)

    elif context['is_light_source']:
        evidence.append(0.55)
        details['is_light_source'] = True
        details['light_distance'] = context['light_distance']
        details['light_strength'] = context['light_strength']
        details['torch_cone'] = has_property('TorchCone', props, 'true')
        details['is_lit_variant'] = (
            'base:litlantern' in context['tags'] or
            has_property('ActivatedItem', props, 'true')
        )

        is_lantern = (
            'lantern' in item_id.lower() or
            'base:litlantern' in context['tags'] or
            'base:unlitlantern' in context['tags']
        )
        if is_lantern:
            details['electronics_type'] = 'Light.Lantern'
            evidence.append(0.2)
        else:
            details['electronics_type'] = 'Light.Flashlight'
            evidence.append(0.2)

        if details['torch_cone']:
            evidence.append(0.05)
        if context['light_distance'] > 0 and context['light_strength'] > 0:
            evidence.append(0.1)

    elif context['is_light_component']:
        details['electronics_type'] = 'Light.Component'
        details['is_light_source'] = False
        evidence.append(0.7)

    elif id_matches_pattern(item_id, BATTERY_PATTERNS):
        details['is_battery'] = True
        details['electronics_type'] = 'Battery'
        evidence.append(0.2)
        evidence.append(0.4)

    elif context['is_general_electronics']:
        evidence.append(0.55)
        details['is_general_electronics'] = True

        if details['is_battery']:
            details['electronics_type'] = 'Battery'
            evidence.append(0.2)
        elif id_matches_pattern(item_id, GENERATOR_PATTERNS) or 'base:generator' in context['tags']:
            details['is_generator'] = True
            details['electronics_type'] = 'Generator'
            evidence.append(0.25)
        elif (
            id_matches_pattern(item_id, ELECTRONIC_COMM_PATTERNS) or
            ('base:miscelectronic' in context['tags'] and id_matches_pattern(item_id, ['Phone', 'Pager', 'Receiver']))
        ):
            details['is_communication'] = True
            details['electronics_type'] = 'Gadget.Communication'
            evidence.append(0.2)
        elif id_matches_pattern(item_id, ELECTRONIC_AUDIO_PATTERNS):
            details['electronics_type'] = 'Gadget.Audio'
            evidence.append(0.2)
        elif (
            id_matches_pattern(item_id, ELECTRONIC_CONTROL_PATTERNS) or
            'base:tvremote' in context['tags']
        ):
            details['electronics_type'] = 'Gadget.Control'
            evidence.append(0.2)
        elif any(tag in context['tags'] for tag in ELECTRONIC_GENERAL_TAGS):
            details['electronics_type'] = 'Gadget.General'
            evidence.append(0.15)
        else:
            details['electronics_type'] = 'Gadget.General'
            evidence.append(0.1)

    elif id_matches_pattern(item_id, GENERATOR_PATTERNS):
        details['is_generator'] = True
        details['electronics_type'] = 'Generator'
        evidence.append(0.2)
        evidence.append(0.4)
    elif id_matches_pattern(item_id, COMMUNICATION_PATTERNS):
        details['is_communication'] = True
        details['electronics_type'] = 'Gadget.Radio'
        evidence.append(0.2)
        evidence.append(0.4)
    elif (
        id_matches_pattern(item_id, ['Flashlight', 'PenLight', 'HandTorch', 'LightBulb']) or
        any(tag in context['tags'] for tag in LIGHT_TAG_PATTERNS)
    ):
        details['electronics_type'] = 'Light.Flashlight'
        evidence.append(0.55)
    else:
        details['electronics_type'] = 'Gadget'
        evidence.append(0.4)

    if context['requires_power']:
        evidence.append(0.15)
        details['requires_power'] = True

    if context['has_signal']:
        evidence.append(0.1)
        details['has_signal'] = True

    confidence = min(1.0, sum(evidence)) if evidence else 0.0
    matches = confidence > 0.4

    return matches, confidence, details


def get_electronics_tags(item_id, props):
    """
    Generate electronics tags based on signature match.
    
    Args:
        item_id: Item identifier
        props: Properties string
    
    Returns:
        list: Tag list for this electronic item
    """
    matches, confidence, details = matches_electronics_signature(item_id, props)
    
    if not matches:
        return []
    
    tags = []
    
    # Primary tag
    elec_type = details.get('electronics_type', 'General')
    tags.append(f"Electronics.{elec_type}")

    if details.get('is_battery'):
        tags.append("Electronics.PowerSource")
    if details.get('is_generator'):
        tags.append("Electronics.PowerGenerator")
    if details.get('is_communication'):
        tags.append("Electronics.Communicator")
    if details.get('is_two_way'):
        tags.append("Electronics.Radio.TwoWay")
    elif details.get('electronics_type') == 'Radio.Broadcast':
        tags.append("Electronics.Radio.Broadcast")
    if details.get('is_portable'):
        tags.append("Electronics.Portable")
    if details.get('requires_power'):
        tags.append("Electronics.RequiresPower")
    if details.get('has_signal'):
        tags.append("Electronics.Transmitter")
    if details.get('is_light_source'):
        tags.append("Electronics.LightSource")
    
    return tags
