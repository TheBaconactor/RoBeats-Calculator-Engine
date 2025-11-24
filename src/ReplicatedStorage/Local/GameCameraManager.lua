-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:25 PM
-- Cached decompilation

require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_1 = require(game.ReplicatedStorage.Shared.GameSlot)
local v_u_2 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.DebugOut)
return {
    ["new"] = function(_, p_u_4) --[[ Name: new ]] --[[ Line: 9 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_2, (copy 3): v_u_3 ]]
        local v5 = {}
        local v_u_6 = nil
        local v_u_7 = nil
        local v_u_8 = nil
        local v_u_9 = 1
        local v_u_10 = 1
        v5.cons = function(_) --[[ Name: cons ]] --[[ Line: 18 ]]
            --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_1, (ref 3): v_u_7, (ref 4): v_u_8 ]]
            v_u_6 = workspace.CurrentCamera
            v_u_6.CFrame = v_u_1:slot_to_camera_cframe(1)
            v_u_6.CameraType = Enum.CameraType.Scriptable
            v_u_6.CameraSubject = nil
            v_u_7 = v_u_6.CFrame
            v_u_8 = v_u_6.CFrame
        end;
        local function f_get_camera_final_cframe(p11) --[[ Name: get_camera_final_cframe ]] --[[ Line: 28 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_2, (ref 3): v_u_3, (ref 4): v_u_1 ]]
            if not p_u_4:show_fullscreen_mobile_ui() then
                return v_u_1:slot_to_camera_cframe(p11);
            end;
            local v12 = (Vector3.new(0, -1, -10)):Lerp(Vector3.new(0, 2, -7), v_u_2:YForPointOf2PtLineP1P2X(2.1041095890410957, 0, 1.3333333333333333, 1, v_u_3:screen_size().X / v_u_3:screen_size().Y))
            local v13 = v_u_1:slot_to_camera_cframe(p11)
            local v14 = v13 - v13.p
            local v15 = v13.p + v14 * v12
            return CFrame.new(v15, v15 + v14 * Vector3.new(0, -0.325, -1));
        end;
        v5.set_camera_focus_pos = function(_, p_u_16) --[[ Name: set_camera_focus_pos ]] --[[ Line: 44 ]]
            --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_6 ]]
            v_u_3:ptry(function() --[[ Line: 45 ]]
                --[[ Upvalues: (ref 1): v_u_6, (copy 2): p_u_16 ]]
                v_u_6.Focus = CFrame.new(p_u_16)
            end)
        end;
        v5.camera_setup_world = function(p17) --[[ Name: camera_setup_world ]] --[[ Line: 50 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_7, (ref 3): v_u_1, (ref 4): v_u_8, (copy 5): f_get_camera_final_cframe, (ref 6): v_u_6, (ref 7): v_u_9, (ref 8): v_u_10 ]]
            local v18, v19, v20, v21 = p_u_4._world_effect_manager:should_do_game_start_zoom_in_effect()
            if v18 then
                v_u_7 = v_u_1:slot_to_camera_cframe(p_u_4:get_local_game_slot(), v19, v20, 0)
                v_u_8 = f_get_camera_final_cframe(p_u_4:get_local_game_slot())
                v_u_6.CFrame = v_u_7
                p17:set_camera_focus_pos(v_u_8.Position)
                v_u_9 = 0
                v_u_10 = v21
            else
                v_u_7 = f_get_camera_final_cframe(p_u_4:get_local_game_slot())
                v_u_8 = f_get_camera_final_cframe(p_u_4:get_local_game_slot())
                v_u_6.CFrame = v_u_7
                p17:set_camera_focus_pos(v_u_8.Position)
                v_u_9 = 1
                v_u_10 = v21
            end;
            p_u_4._world_effect_manager:game_camera_transition(v_u_9)
        end;
        v5.update = function(_, p22) --[[ Name: update ]] --[[ Line: 72 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_8, (copy 3): f_get_camera_final_cframe, (ref 4): v_u_9, (ref 5): v_u_2, (ref 6): v_u_10, (ref 7): v_u_6, (ref 8): v_u_7, (ref 9): v_u_3 ]]
            if p_u_4._spui:is_layout_updated() then
                v_u_8 = f_get_camera_final_cframe(p_u_4:get_local_game_slot())
            end;
            if v_u_9 < 1 then
                v_u_9 = v_u_2:IncrementClamp(v_u_9, p22 * v_u_2:SecondsToTick(v_u_10), 0, 1)
                v_u_6.CFrame = v_u_7:lerp(v_u_8, v_u_2:BezierPt2ForT(0, 0, 1, 0, 0, 1, 1, 1, v_u_9).Y)
                v_u_3:update()
            else
                v_u_6.CFrame = v_u_8
            end;
            p_u_4._world_effect_manager:game_camera_transition(v_u_9)
        end;
        v5.camera_transitioning = function(_) --[[ Name: camera_transitioning ]] --[[ Line: 95 ]]
            --[[ Upvalues: (ref 1): v_u_9 ]]
            return v_u_9 < 1;
        end;
        v5.finish_camera_transition = function(p23) --[[ Name: finish_camera_transition ]] --[[ Line: 97 ]]
            --[[ Upvalues: (ref 1): v_u_9 ]]
            v_u_9 = 1
            p23:update(0)
        end;
        v5.focus_camera_on_game_slot = function(_, p24) --[[ Name: focus_camera_on_game_slot ]] --[[ Line: 102 ]]
            --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_6, (ref 3): v_u_8, (copy 4): f_get_camera_final_cframe, (ref 5): v_u_9, (ref 6): v_u_10 ]]
            v_u_7 = v_u_6.CFrame
            v_u_8 = f_get_camera_final_cframe(p24)
            v_u_9 = 0
            v_u_10 = 0.75
        end;
        v5:cons()
        return v5;
    end
};
