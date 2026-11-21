/** SCP N03D-BF: exact public original third-party Three procedural runtime lower-body
 * source trace for Blender pose bridge. No real force/contact nor private model.
 */
import assert from 'node:assert/strict';
import { writeFileSync } from 'node:fs';
import { it } from 'node:test';
import type { Bone } from 'three';
import { createWorld } from './helpers/sim.ts';

it('exports source-exact 360x60Hz original procedural bone-local rotations and live support-state witnesses', () => {
  assert.ok(process.env.SCP_BF_OUT);
  const w=createWorld();
  const h=w.human;
  const bones:Record<string,Bone>={
    Hips:h.rig.hips,
    LeftHip:h.rig.left.thigh,LeftKnee:h.rig.left.shin,
    LeftAnkle:h.rig.left.foot,
    LeftToe:h.rig.left.toe!,
    RightHip:h.rig.right.thigh,RightKnee:h.rig.right.shin,
    RightAnkle:h.rig.right.foot,
    RightToe:h.rig.right.toe!,
  };
  assert.ok(Object.values(bones).every(b=>b?.isBone));
  const quaternion=(b:Bone):number[]=>[b.quaternion.w,b.quaternion.x,b.quaternion.y,b.quaternion.z].map(x=>Number(x.toFixed(9)));
  const translation=(v:{x:number,y:number,z:number}):number[]=>[v.x,v.y,v.z].map(x=>Number(x.toFixed(9)));
  const rest=Object.fromEntries(Object.entries(bones).map(([k,b])=>[k,{node_name:b.name,quat_wxyz:quaternion(b)}]));
  const sourceModel=process.env.PH_MODEL!;
  const sourceMapping=process.env.PH_MAPPING!;
  const frames:any[]=[];
  h.targetSpeed=1;
  for (let i=0;i<120;i++)h.update(1/60);
  const initial=translation(h.position);
  for (let i=0;i<360;i++) {
    h.update(1/60);
    w.model.updateMatrixWorld(true);
    const pose=Object.fromEntries(Object.entries(bones).map(([k,b])=>[k,quaternion(b)]));
    const landmarks=Object.fromEntries(Object.entries(bones).map(([k,b])=>{
      const pt=b.getWorldPosition(new (b.position.constructor as any)());
      return [k,translation(pt)];
    }));
    frames.push({i,pose,root_y_up:translation(h.position),
       phases:{L:h.locomotion.feet.left.phase,R:h.locomotion.feet.right.phase},
       planted_world:{L:translation(h.locomotion.feet.left.planted),
                      R:translation(h.locomotion.feet.right.planted)},
       landmarks_world_y_up:landmarks});
  }
  assert.equal(frames.length,360);
  assert.ok(new Set(frames.map(f=>f.pose.LeftKnee.join(','))).size>50,'NO_CONTROLLER_KNEE_MOVEMENT');
  const doc={schema:'scp.n03d-bf.real-three-to-blender-source-pose-v1',
             original_source_commit:process.env.SCP_UPSTREAM_COMMIT,
             source_glb_model:sourceModel,source_mapping:sourceMapping,
             public_original_cc0_only:true,
             genuine_realtime_three_frames_60hz:360,
             warmup_frames:120,
             same_original_motion_for_blender_replay:true,
             bone_rest_map:rest,
             initial_root_y_up:initial,
             source_native_leg_length_m:h.legLength,
             frames,
             planted_targets_are_not_measured_skin_contact:true,
             original_100style_motion_identical:false,
             source_grf_measured:false,physical_gait_accepted:false,mvp_accepted:false};
  assert.ok(doc.source_native_leg_length_m>0.4 && doc.source_native_leg_length_m<1.5);
  writeFileSync(process.env.SCP_BF_OUT!,JSON.stringify(doc)+'\n');
  console.log('N03D_BF_REAL_SOURCE_CONTROLLER_RECORDED',JSON.stringify({
    model:sourceModel,mapping:sourceMapping,frames:360,full_foot_rest_names:rest,
    source_leg_length:h.legLength,source_ground_force:false}),);
});
