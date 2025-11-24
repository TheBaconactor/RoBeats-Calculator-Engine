-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:22:08 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.GameStage.StageInfoBase)
local v_u_2 = require(game.ReplicatedStorage.Shared.Override)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_4 = require(game.ReplicatedStorage.Shared.GameSlot)
require(game.ReplicatedStorage.Shared.SPVector)
require(game.ReplicatedStorage.Shared.PlayerSettings)
require(game.ReplicatedStorage.Shared.BrightnessSettings)
local v_u_5 = require(game.ReplicatedStorage.Shared.ModelLoadDB)
local v_u_6 = require(game.ReplicatedStorage.Shared.ModelLoadDBAsset)
local v_u_7 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_8 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_9 = require(game.ReplicatedStorage.Shared.RotatingCFrameObject)
require(game.ReplicatedStorage.Local.AnimationManager)
local v_u_10 = require(game.ReplicatedStorage.GameStage.Util.MovingModel)
require(game.ReplicatedStorage.PlayerInfo.DanceDatabase)
local v_u_11 = nil
local v_u_12 = nil
local v_u_13 = nil
require(game.ReplicatedStorage.Shared.Dependency):require_client(function() --[[ Line: 23 ]]
    --[[ Upvalues: (ref 1): v_u_11, (ref 2): v_u_12, (ref 3): v_u_13 ]]
    v_u_11 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
    v_u_12 = require(game.ReplicatedStorage.GameStage.Util.GameStageDefaultCharacterShineBehaviour)
    v_u_13 = require(game.ReplicatedStorage.Effects.CharacterShineEffect)
end)
return {
    ["new"] = function(_) --[[ Name: new ]] --[[ Line: 31 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_2, (copy 3): v_u_5, (copy 4): v_u_6, (copy 5): v_u_8, (ref 6): v_u_11, (copy 7): v_u_9, (copy 8): v_u_10, (ref 9): v_u_12, (copy 10): v_u_4, (copy 11): v_u_7, (copy 12): v_u_3 ]]
        local v14 = v_u_1:new()
        v_u_2:get_base_fn(v14, "get_name")
        v14.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 35 ]]
            return "Skyborne Sanctuary";
        end;
        v_u_2:get_base_fn(v14, "get_icon")
        v14.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 37 ]]
            return "rbxassetid://118482390237470";
        end;
        local v_u_15 = nil
        v14.load_stage = function(_, p_u_16) --[[ Name: load_stage ]] --[[ Line: 40 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_6, (ref 3): v_u_15 ]]
            v_u_5:singleton():load_model_category(v_u_6.GameStage.SkyIslandsStage, v_u_6.Category.GameStage, function(p17) --[[ Line: 41 ]]
                --[[ Upvalues: (ref 1): v_u_15, (copy 2): p_u_16 ]]
                v_u_15 = p17
                p_u_16()
            end)
        end;
        local v_u_18 = nil
        local v_u_19 = nil
        local v_u_20 = nil
        local v_u_21 = v_u_8:new()
        local v_u_22 = v_u_8:new()
        local v_u_23 = nil
        local v_u_24 = nil
        local v_u_25 = CFrame.new()
        local v_u_26 = CFrame.new()
        local v_u_27 = nil
        local v_u_28 = 0
        local function f_recalc_airship() --[[ Name: recalc_airship ]] --[[ Line: 61 ]]
            --[[ Upvalues: (ref 1): v_u_18, (ref 2): v_u_24, (ref 3): v_u_8, (ref 4): v_u_25, (ref 5): v_u_26, (ref 6): v_u_27 ]]
            local l_Airship_0 = v_u_18.Airship
            v_u_24 = l_Airship_0.Asset
            local v29 = v_u_8:new({
                v_u_8:new({ l_Airship_0.Anchors1.Start, l_Airship_0.Anchors1.End }),
                v_u_8:new({ l_Airship_0.Anchors2.Start, l_Airship_0.Anchors2.End }),
                v_u_8:new({ l_Airship_0.Anchors3.Start, l_Airship_0.Anchors3.End }),
                v_u_8:new({ l_Airship_0.Anchors4.Start, l_Airship_0.Anchors4.End })
            }):random()
            v_u_25 = v29:get(1).CFrame
            v_u_26 = v29:get(2).CFrame
            v_u_27 = v_u_24.Airship.Propeller
        end;
        v_u_2:get_base_fn(v14, "setup_stage")
        v14.setup_stage = function(p30, p31) --[[ Name: setup_stage ]] --[[ Line: 77 ]]
            --[[ Upvalues: (ref 1): v_u_15, (ref 2): v_u_11, (ref 3): v_u_18, (ref 4): v_u_23, (copy 5): v_u_21, (ref 6): v_u_9, (ref 7): v_u_8, (ref 8): v_u_10, (copy 9): v_u_22, (copy 10): f_recalc_airship, (ref 11): v_u_19, (ref 12): v_u_20, (ref 13): v_u_12 ]]
            v_u_15.Parent = v_u_11:get_local_elements_folder()
            local v32 = v_u_11:get_game_sky()
            v32.SkyboxBk = "rbxassetid://600830446"
            v32.SkyboxDn = "rbxassetid://600831635"
            v32.SkyboxFt = "rbxassetid://600832720"
            v32.SkyboxLf = "rbxassetid://600886090"
            v32.SkyboxRt = "rbxassetid://600833862"
            v32.SkyboxUp = "rbxassetid://600835177"
            local v33 = v_u_11:get_game_lighting()
            v33.Ambient = Color3.fromRGB(139, 83, 81)
            v33.Brightness = 0.8
            v33.ColorShift_Bottom = Color3.new(0.764706, 0.470588, 0)
            v33.ColorShift_Top = Color3.new(0.392157, 0.34902, 0.2)
            v33.OutdoorAmbient = Color3.new(0.498039, 0.498039, 0.498039)
            v33.ClockTime = 12
            v33.GeographicLatitude = 45
            v_u_18 = v_u_15.FaceToPlayer
            v_u_23 = v_u_18.TrackPlatform.Union
            p30:on_switch_focus_slot(p31)
            v_u_21:clear()
            v_u_21:push_back(v_u_9:new(v_u_18.RotationBG.CloudRing1):set_rotate_time_sec(225))
            v_u_21:push_back(v_u_9:new(v_u_18.RotationBG.CloudRing2):set_rotate_time_sec(481):set_rotation_axis(Vector3.new(0, -1, 0)))
            v_u_21:push_back(v_u_9:new(v_u_18.RotationBG.CloudBottom1):set_rotate_time_sec(301):set_rotation_axis(Vector3.new(0, -1, 0)))
            v_u_21:push_back(v_u_9:new(v_u_18.RotationBG.CloudBottom2):set_rotate_time_sec(236))
            v_u_8:for_each(v_u_8:new(v_u_18.MovingModels:GetChildren()), function(p34) --[[ Line: 121 ]]
                --[[ Upvalues: (ref 1): v_u_10, (ref 2): v_u_22 ]]
                v_u_22:push_back((v_u_10:new(p34)))
            end)
            f_recalc_airship()
            v_u_19 = v_u_18.CharacterShineProto
            v_u_19.Parent = nil
            v_u_20 = v_u_12:new(v_u_19, Vector3.new(0, -3.5, 0))
        end;
        v_u_2:get_base_fn(v14, "on_switch_focus_slot")
        v14.on_switch_focus_slot = function(_, p35) --[[ Name: on_switch_focus_slot ]] --[[ Line: 137 ]]
            --[[ Upvalues: (ref 1): v_u_18, (ref 2): v_u_4, (copy 3): v_u_22 ]]
            v_u_18:SetPrimaryPartCFrame(CFrame.new(v_u_4:get_world_center_position(), v_u_4:slot_to_world_position(p35:get_local_game_slot())))
            for _, v36 in v_u_22:key_itr() do
                v36:recalc_positions()
            end;
        end;
        v_u_2:get_base_fn(v14, "teardown_stage")
        v14.teardown_stage = function(_, p37) --[[ Name: teardown_stage ]] --[[ Line: 148 ]]
            --[[ Upvalues: (ref 1): v_u_18, (ref 2): v_u_19, (ref 3): v_u_23, (copy 4): v_u_21, (copy 5): v_u_22, (ref 6): v_u_20, (ref 7): v_u_24, (ref 8): v_u_27, (ref 9): v_u_15 ]]
            v_u_18 = nil
            v_u_19:Destroy()
            v_u_23 = nil
            v_u_21:clear()
            v_u_22:clear()
            v_u_20:teardown(p37)
            v_u_24 = nil
            v_u_27 = nil
            v_u_15:Destroy()
        end;
        v_u_2:get_base_fn(v14, "create_shine_for_slot_at_cframe")
        v14.create_shine_for_slot_at_cframe = function(_, p38, p39, p40) --[[ Name: create_shine_for_slot_at_cframe ]] --[[ Line: 163 ]]
            --[[ Upvalues: (ref 1): v_u_20 ]]
            v_u_20:create_shine_for_slot_at_cframe(p38, p39, p40)
        end;
        local function _(p41, p42) --[[ Name: cframe_with_z_orientation ]] --[[ Line: 167 ]]
            local l_Position_0 = p41.Position
            local v43, v44, _ = p41:ToEulerAnglesXYZ()
            return CFrame.new(l_Position_0) * CFrame.Angles(v43, v44, p42);
        end;
        v_u_2:get_base_fn(v14, "game_update")
        v14.game_update = function(_, p45, p46) --[[ Name: game_update ]] --[[ Line: 178 ]]
            --[[ Upvalues: (ref 1): v_u_20, (copy 2): v_u_21, (copy 3): v_u_22, (ref 4): v_u_24, (ref 5): v_u_25, (ref 6): v_u_26, (ref 7): v_u_27, (ref 8): v_u_28, (ref 9): v_u_7 ]]
            v_u_20:update(p45, p46)
            for _, v47 in v_u_21:key_itr() do
                v47:update_obj_cframe(p45)
            end;
            for _, v48 in v_u_22:key_itr() do
                v48:update(p45)
            end;
            if v_u_24 then
                v_u_24:SetPrimaryPartCFrame(v_u_25:Lerp(v_u_26, p46:es_gamelocal_get_audiomanager():get_current_time_ms() / p46:es_gamelocal_get_audiomanager():get_song_length_ms()))
            end;
            if v_u_27 then
                v_u_28 = (v_u_28 + v_u_7:sec_to_tick(12.5) * 6.283185307179586 * p45) % 6.283185307179586
                local v49 = v_u_27:GetPrimaryPartCFrame()
                local v50 = v_u_28
                local l_Position_1 = v49.Position
                local v51, v52, _ = v49:ToEulerAnglesXYZ()
                v_u_27:SetPrimaryPartCFrame(CFrame.new(l_Position_1) * CFrame.Angles(v51, v52, v50))
            end;
        end;
        v14.should_do_game_start_zoom_in_effect = function(_) --[[ Name: should_do_game_start_zoom_in_effect ]] --[[ Line: 199 ]]
            return true, 36.5, 28, 0.75;
        end;
        v14.game_camera_transition = function(_, p_u_53) --[[ Name: game_camera_transition ]] --[[ Line: 204 ]]
            --[[ Upvalues: (ref 1): v_u_23, (ref 2): v_u_3, (ref 3): v_u_7 ]]
            if v_u_23 then
                v_u_3:ptry(function() --[[ Line: 206 ]]
                    --[[ Upvalues: (ref 1): v_u_23, (ref 2): v_u_3, (ref 3): v_u_7, (copy 4): p_u_53 ]]
                    v_u_23.Transparency = v_u_3:tra(v_u_7:YForPointOf2PtLineP1P2X(0, 0, 1, 0.35, p_u_53))
                end)
            end;
        end;
        return v14;
    end
};
