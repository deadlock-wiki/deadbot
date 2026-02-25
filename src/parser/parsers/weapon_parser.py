from typing import Dict, Any
from utils.num_utils import convert_engine_units_to_meters, round_sig_figs


def parse_weapon_info(weapon_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parses a 'm_WeaponInfo' block for a primary or alternate fire mode.
    Returns a dictionary of parsed weapon stats.
    """
    stats = {}

    # Core Stats
    stats['BulletSpeed'] = convert_engine_units_to_meters(weapon_info.get('m_flBulletSpeed'))
    stats['BulletDamage'] = weapon_info.get('m_flBulletDamage', 0)
    stats['RoundsPerSecond'] = round_sig_figs(calculate_fire_rate(weapon_info), 5)
    stats['ClipSize'] = weapon_info.get('m_iClipSize')
    stats['ReloadTime'] = weapon_info.get('m_reloadDuration')
    stats['ReloadMovespeed'] = float(weapon_info.get('m_flReloadMoveSpeed', '0')) / 10000
    stats['ReloadDelay'] = weapon_info.get('m_flReloadSingleBulletsInitialDelay', 0)
    stats['ReloadSingle'] = weapon_info.get('m_bReloadSingleBullets', False)

    # Falloff and Range
    stats['FalloffStartRange'] = convert_engine_units_to_meters(weapon_info.get('m_flDamageFalloffStartRange', 0))
    stats['FalloffEndRange'] = convert_engine_units_to_meters(weapon_info.get('m_flDamageFalloffEndRange', 0))
    stats['FalloffStartScale'] = weapon_info.get('m_flDamageFalloffStartScale', 1.0)
    stats['FalloffEndScale'] = weapon_info.get('m_flDamageFalloffEndScale', 1.0)
    stats['FalloffBias'] = weapon_info.get('m_flDamageFalloffBias', 0.5)

    # Bullet Properties
    stats['BulletGravityScale'] = weapon_info.get('m_flBulletGravityScale', 0)
    stats['BulletsPerShot'] = weapon_info.get('m_iBullets', 1)
    stats['BulletsPerBurst'] = weapon_info.get('m_iBurstShotCount', 1)
    stats['BurstInterShotInterval'] = weapon_info.get('m_flIntraBurstCycleTime', 0)
    stats['ShootMoveSpeed'] = weapon_info.get('m_flShootMoveSpeedPercent', 1.0)
    stats['HitOnceAcrossAllBullets'] = weapon_info.get('m_bHitOnceAcrossAllBullets', False)
    stats['CanCrit'] = weapon_info.get('m_bCanCrit', True)
    stats['AmmoConsumedPerShot'] = weapon_info.get('m_iAmmoConsumedPerShot', 1)

    # Explosive Properties (often for alt-fire)
    if 'm_flExplosionRadius' in weapon_info:
        stats['ExplosionRadius'] = convert_engine_units_to_meters(weapon_info['m_flExplosionRadius'])
    if 'm_flExplosionDamageScaleAtMaxRadius' in weapon_info:
        stats['ExplosionDamageScaleAtMaxRadius'] = weapon_info['m_flExplosionDamageScaleAtMaxRadius']

    # Spin-up Properties
    if weapon_info.get('m_bSpinsUp'):
        max_spin_cycle_time = weapon_info.get('m_flMaxSpinCycleTime')
        stats['RoundsPerSecondAtMaxSpin'] = 1 / max_spin_cycle_time if max_spin_cycle_time and max_spin_cycle_time > 0 else 0
        stats['SpinAcceleration'] = weapon_info.get('m_flSpinIncreaseRate', 0)
        stats['SpinDeceleration'] = weapon_info.get('m_flSpinDecayRate', 0)

    # Calculate DPS
    dps_stats = get_dps_calculation_stats(stats)
    if dps_stats.get('RoundsPerSecond', 0) > 0:
        stats['DPS'] = round_sig_figs(calculate_dps(dps_stats, 'burst'), 5)
        stats['SustainedDPS'] = round_sig_figs(calculate_dps(dps_stats, 'sustained'), 5)

    return stats


def get_dps_calculation_stats(weapon_stats: Dict[str, Any]) -> Dict[str, Any]:
    """Returns a dictionary of stats used to calculate DPS"""
    return {
        'ReloadSingle': weapon_stats.get('ReloadSingle'),
        'ReloadDelay': weapon_stats.get('ReloadDelay'),
        'ReloadTime': weapon_stats.get('ReloadTime'),
        'ClipSize': weapon_stats.get('ClipSize'),
        'RoundsPerSecond': (
            weapon_stats.get('RoundsPerSecondAtMaxSpin')
            if 'SpinAcceleration' in weapon_stats and weapon_stats.get('RoundsPerSecondAtMaxSpin')
            else weapon_stats.get('RoundsPerSecond')
        ),
        'BurstInterShotInterval': weapon_stats.get('BurstInterShotInterval'),
        'BulletDamage': weapon_stats.get('BulletDamage'),
        'BulletsPerShot': weapon_stats.get('BulletsPerShot'),
        'BulletsPerBurst': weapon_stats.get('BulletsPerBurst'),
        'HitOnceAcrossAllBullets': weapon_stats.get('HitOnceAcrossAllBullets'),
    }


def calculate_dps(dps_stats: Dict[str, Any], dps_type: str = 'burst') -> float:
    """
    Calculates Burst or Sustained DPS of a weapon.

    Args:
        dps_stats: Dictionary containing weapon stats for calculation
        dps_type: Either 'burst' or 'sustained'
    """
    # Burst, not to be confused with burst as in burst fire, but rather
    # a burst of damage where delta time is 0.
    # Sustained has a delta time of infinity, meaning it takes into
    # account time-to-empty-clip and reload time.
    stats = {k: v for k, v in dps_stats.items() if v is not None}

    if stats.get('RoundsPerSecond', 0) == 0:
        return 0

    # If damage is dealt once for all bullets (e.g. shotguns), treat as 1 bullet for DPS
    bullets_per_shot = 1 if stats.get('HitOnceAcrossAllBullets') else stats.get('BulletsPerShot', 1)
    cycle_time = 1 / stats['RoundsPerSecond']
    total_cycle_time = cycle_time * stats.get('BulletsPerBurst', 1)

    if total_cycle_time == 0:
        return 0

    # Burst DPS accounts for burst weapons and assumes maximum spinup (if applicable)
    if dps_type == 'burst':
        dps = stats.get('BulletDamage', 0) * bullets_per_shot * stats.get('BulletsPerBurst', 1) / total_cycle_time
        return dps

    # Sustained DPS also accounts for reloads/clipsize
    elif dps_type == 'sustained':
        clip_size = stats.get('ClipSize', 0)
        if clip_size <= 0:
            # For weapons with no clip (like Bebop's beam), sustained DPS is the same as burst DPS
            sustained_dps = stats.get('BulletDamage', 0) * bullets_per_shot * stats.get('BulletsPerBurst', 1) / total_cycle_time
            return sustained_dps

        # All reload actions have ReloadDelay played first,
        # but typically only single bullet reloads have a non-zero delay
        if stats.get('ReloadSingle'):
            # If reloading 1 bullet at a time, reload time is actually per bullet
            time_to_reload = stats.get('ReloadTime', 0) * clip_size
        else:
            time_to_reload = stats.get('ReloadTime', 0)

        time_to_reload += stats.get('ReloadDelay', 0)
        time_to_empty_clip = clip_size / stats.get('BulletsPerBurst', 1) * total_cycle_time
        # BulletsPerShot doesn't consume more ammo, but BulletsPerBurst does.
        damage_from_clip = stats.get('BulletDamage', 0) * bullets_per_shot * clip_size

        total_time = time_to_empty_clip + time_to_reload
        if total_time == 0:
            return 0

        sustained_dps = damage_from_clip / total_time
        return sustained_dps

    else:
        raise Exception('Invalid DPS type, must be one of: ' + ', '.join(['burst', 'sustained']))


def calculate_fire_rate(weapon_info: Dict[str, Any]) -> float:
    """
    Calculates the rounds per second of a mouse click by dividing the total bullets per shot
    by the total shot time, taking consideration of the cooldown between shots during a burst
    """
    shot_cd = weapon_info.get('m_flCycleTime', 0)
    burst_cd = weapon_info.get('m_flBurstShotCooldown', 0)
    intra_burst_cd = weapon_info.get('m_flIntraBurstCycleTime', 0)
    bullets_per_shot = weapon_info.get('m_iBurstShotCount', 0)

    total_shot_time = bullets_per_shot * intra_burst_cd + shot_cd + burst_cd

    return bullets_per_shot / total_shot_time if total_shot_time > 0 else 0
