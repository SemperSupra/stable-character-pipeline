/** SCP N03D-BB: real upstream Three locomotion runtime 6s original-CC0 rig, independent model envelope.
 * Copied into ephemeral pinned upstream tests only. Pose/support metrics are kinematic
 * proxies; no CC0 Blender evaluated shoe or ground reaction force claim.
 */
import assert from 'node:assert/strict';
import { writeFileSync } from 'node:fs';
import { describe, it } from 'node:test';
import { createWorld, simulate } from './helpers/sim.ts';

describe('scp real source-exact MPFB-adjacent Rigify/Mixamo locomotion bridge', () => {
  it('executes 360 true fixed 60Hz motion frames and reports bounded foot controls', () => {
    const world=createWorld();
    const warm=simulate(world,2,[[0,h=>{h.targetSpeed=1;}]],{dt:1/60});
    assert.equal(warm.frames,120);
    const rec=simulate(world,6,[],{dt:1/60,start:2});
    assert.equal(rec.frames,360);
    assert.ok(rec.finiteOK,'nonfinite pelvis or root');
    assert.ok(rec.alternates,'no alternating foot takeoffs');
    assert.ok(Number.isFinite(rec.slip) && rec.slip>=0,'planted target slip nonfinite');
    assert.ok(Number.isFinite(rec.stanceIK) && rec.stanceIK>=0,'stance IK error nonfinite');
    assert.ok(Number.isFinite(rec.toeClearance),'toe clearance invalid');
    const out={
      schema:'scp.n03d-bb.kinematic-three-original-cc0.v1',
      source_library_commit:process.env.SCP_UPSTREAM_COMMIT,
      model:process.env.PH_MODEL,
      mapping:process.env.PH_MAPPING,
      model_asset_qualified_upstream_through_BA:false,
      source_class:'PUBLIC_CC0_CANDIDATE_UPSTREAM_RIGHTS_UNMERGED',
      prewarm_frames:120,actual_native_three60hz_frames:360,
      render_or_blender_native_shoe:false,
      model_ground_force_measured:false,
      measured_physics_accepted:false,
      true_anatomical_foot_labels_certified:false,
      planted_target_slip_m:rec.slip,
      native_three_stance_ik_max_error_m:rec.stanceIK,
      native_three_swing_toe_clearance_m:rec.toeClearance,
      max_horizontal_velocity_mps:rec.maxSpeed,
      source_scene_100style_identical:false,
      takeoff_sequence:rec.liftoffs,
      alternating_steps:rec.alternates,
      pelvis_drop_normalized:rec.hipDrop,
      pelvis_jerk_per_frame2_m:rec.hipJerk,
      total_frames:rec.frames,
      mvp_accepted:false,status:'PASS_NARROW_THREE_KINEMATICS_HOLD_BLENDER_PHYSICS'
    };
    assert.ok(rec.slip<=1e-6,'procedural planted targets slipped');
    assert.ok(rec.stanceIK<.001,'procedural IK foot target error');
    assert.ok(rec.toeClearance>-.005,'toe crossed reference ground beyond tolerance');
    assert.ok(rec.liftoffs.length>=4,'no actual walking phases');
    assert.ok(out.mvp_accepted===false && out.model_ground_force_measured===false);
    writeFileSync(process.env.SCP_OUT!,JSON.stringify(out,null,2)+'\n','utf8');
    console.log('N03D_BB_ACTUAL_THREE_LOCOMOTION',JSON.stringify(out));
  });
});
