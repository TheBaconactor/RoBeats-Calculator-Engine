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
local v_u_11 = require(game.ReplicatedStorage.PlayerInfo.DanceDatabase)
local v_u_12 = nil
local v_u_13 = nil
local v_u_14 = nil
require(game.ReplicatedStorage.Shared.Dependency):require_client(function() --[[ Line: 23 ]]
    --[[ Upvalues: (ref 1): v_u_12, (ref 2): v_u_13, (ref 3): v_u_14 ]]
    v_u_12 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
    v_u_13 = require(game.ReplicatedStorage.GameStage.Util.GameStageDefaultCharacterShineBehaviour)
    v_u_14 = require(game.ReplicatedStorage.Effects.CharacterShineEffect)
end)
return {
    ["new"] = function(_) --[[ Name: new ]] --[[ Line: 31 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_2, (copy 3): v_u_5, (copy 4): v_u_6, (copy 5): v_u_8, (ref 6): v_u_12, (copy 7): v_u_9, (copy 8): v_u_3, (copy 9): v_u_11, (copy 10): v_u_10, (ref 11): v_u_13, (copy 12): v_u_4, (copy 13): v_u_7 ]]
        local v15 = v_u_1:new()
        v_u_2:get_base_fn(v15, "get_name")
        v15.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 35 ]]
            return "Caught in the Clouds";
        end;
        v_u_2:get_base_fn(v15, "get_icon")
        v15.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 37 ]]
            return "rbxassetid://18686149580";
        end;
        local v_u_16 = nil
        v15.load_stage = function(_, p_u_17) --[[ Name: load_stage ]] --[[ Line: 40 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_6, (ref 3): v_u_16 ]]
            v_u_5:singleton():load_model_category(v_u_6.GameStage.CloudsStage, v_u_6.Category.GameStage, function(p18) --[[ Line: 41 ]]
                --[[ Upvalues: (ref 1): v_u_16, (copy 2): p_u_17 ]]
                v_u_16 = p18
                p_u_17()
            end)
        end;
        local v_u_19 = nil
        local v_u_20 = nil
        local v_u_21 = nil
        local v_u_22 = v_u_8:new()
        local v_u_23 = v_u_8:new()
        local v_u_24 = nil
        v_u_2:get_base_fn(v15, "setup_stage")
        v15.setup_stage = function(p25, p26) --[[ Name: setup_stage ]] --[[ Line: 56 ]]
            --[[ Upvalues: (ref 1): v_u_16, (ref 2): v_u_12, (ref 3): v_u_19, (ref 4): v_u_24, (copy 5): v_u_22, (ref 6): v_u_9, (ref 7): v_u_8, (ref 8): v_u_3, (ref 9): v_u_11, (ref 10): v_u_10, (copy 11): v_u_23, (ref 12): v_u_20, (ref 13): v_u_21, (ref 14): v_u_13 ]]
            v_u_16.Parent = v_u_12:get_local_elements_folder()
            local v27 = v_u_12:get_game_sky()
            v27.SkyboxBk = "rbxassetid://13451524450"
            v27.SkyboxDn = "rbxassetid://13451528360"
            v27.SkyboxFt = "rbxassetid://13451529407"
            v27.SkyboxLf = "rbxassetid://13451530189"
            v27.SkyboxRt = "rbxassetid://13451530943"
            v27.SkyboxUp = "rbxassetid://13451531756"
            local v28 = v_u_12:get_game_lighting()
            v28.Ambient = Color3.new(0, 0, 0)
            v28.Brightness = 1
            v28.ColorShift_Bottom = Color3.new(0.470588, 0.129412, 0.764706)
            v28.ColorShift_Top = Color3.new(0.14902, 0, 0.647059)
            v28.OutdoorAmbient = Color3.new(0.498039, 0.498039, 0.498039)
            v28.ClockTime = 12
            v28.GeographicLatitude = 45
            v_u_19 = v_u_16.FaceToPlayer
            v_u_24 = v_u_19.TrackPlatform.Union
            p25:on_switch_focus_slot(p26)
            v_u_22:clear()
            v_u_22:push_back(v_u_9:new(v_u_19.RotationBG.CloudRing1):set_rotate_time_sec(225))
            v_u_22:push_back(v_u_9:new(v_u_19.RotationBG.CloudRing2):set_rotate_time_sec(481):set_rotation_axis(Vector3.new(0, -1, 0)))
            local l_ParallaxBGProto_0 = v_u_19.ParallaxBGProto
            l_ParallaxBGProto_0.Parent = nil
            local v_u_29 = v_u_8:new({ l_ParallaxBGProto_0.Cloud1, l_ParallaxBGProto_0.Cloud2, l_ParallaxBGProto_0.Cloud3 })
            v_u_3:for_count(15, function() --[[ Line: 94 ]]
                --[[ Upvalues: (copy 1): v_u_29, (ref 2): v_u_19, (ref 3): v_u_3, (ref 4): v_u_9, (ref 5): v_u_22 ]]
                local v_u_30 = v_u_29:random():Clone()
                v_u_30.Parent = v_u_19.RotationBG
                local v_u_31 = v_u_3:rand_rangef(-20, 40)
                local v_u_32 = v_u_3:rand_rangef(-30, 90)
                local v_u_33 = 100
                v_u_3:ptry(function() --[[ Line: 101 ]]
                    --[[ Upvalues: (copy 1): v_u_30, (copy 2): v_u_31, (copy 3): v_u_32, (ref 4): v_u_33 ]]
                    local l_Cloud_0 = v_u_30.Cloud
                    local l_Position_0 = l_Cloud_0.Position
                    l_Cloud_0.Position = Vector3.new(l_Position_0.X, l_Position_0.Y + v_u_31, l_Position_0.Z + v_u_32)
                    v_u_33 = (l_Cloud_0.Position - v_u_30.PrimaryPart.Position).Magnitude
                end)
                local v34 = 6.283185307179586 * v_u_33 / 4
                local l_CFrame_0 = v_u_30.PrimaryPart.CFrame
                local v36 = v_u_9:new(v_u_30, function() --[[ Line: 116 ]]
                    --[[ Upvalues: (copy 1): l_CFrame_0 ]]
                    return l_CFrame_0;
                end, function(p35, _, _, _, _, _, _) --[[ Line: 119 ]]
                    --[[ Upvalues: (copy 1): v_u_30 ]]
                    v_u_30:SetPrimaryPartCFrame(p35)
                end):set_rotate_time_sec(v34):set_angle(v_u_3:rand_rangef(0, 6.283185307179586))
                if v_u_3:rand_rangef(-1, 1) < 0 then
                    v36:set_rotation_axis(Vector3.new(0, -1, 0))
                end;
                v_u_22:push_back(v36)
            end)
            for _, v37 in v_u_22:key_itr() do
                v37:update_obj_cframe(1)
            end;
            v_u_8:for_each(v_u_8:new(v_u_19.MovingModels:GetChildren()), function(p_u_38) --[[ Line: 137 ]]
                --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_11, (ref 3): v_u_8, (ref 4): v_u_10, (ref 5): v_u_23 ]]
                v_u_3:ptry(function() --[[ Line: 138 ]]
                    --[[ Upvalues: (copy 1): p_u_38, (ref 2): v_u_3, (ref 3): v_u_11, (ref 4): v_u_8 ]]
                    local l_Humanoid_0 = p_u_38.Asset.NPC.Humanoid
                    v_u_3:ptry(function() --[[ Line: 140 ]]
                        --[[ Upvalues: (copy 1): l_Humanoid_0, (ref 2): v_u_11, (ref 3): v_u_8 ]]
                        l_Humanoid_0:LoadAnimation(v_u_11:singleton():get_dance_animation_for_id(v_u_8:new({
                            4,
                            5,
                            7,
                            10,
                            34,
                            86,
                            150,
                            13
                        }):random())):Play()
                    end)
                end)
                v_u_23:push_back((v_u_10:new(p_u_38)))
            end)
            v_u_20 = v_u_19.CharacterShineProto
            v_u_20.Parent = nil
            v_u_21 = v_u_13:new(v_u_20, Vector3.new(0, -3.5, 0))
        end;
        v_u_2:get_base_fn(v15, "on_switch_focus_slot")
        v15.on_switch_focus_slot = function(_, p39) --[[ Name: on_switch_focus_slot ]] --[[ Line: 170 ]]
            --[[ Upvalues: (ref 1): v_u_19, (ref 2): v_u_4, (copy 3): v_u_23 ]]
            v_u_19:SetPrimaryPartCFrame(CFrame.new(v_u_4:get_world_center_position(), v_u_4:slot_to_world_position(p39:get_local_game_slot())))
            for _, v40 in v_u_23:key_itr() do
                v40:recalc_positions()
            end;
        end;
        v_u_2:get_base_fn(v15, "teardown_stage")
        v15.teardown_stage = function(_, p41) --[[ Name: teardown_stage ]] --[[ Line: 181 ]]
            --[[ Upvalues: (ref 1): v_u_19, (ref 2): v_u_20, (ref 3): v_u_24, (copy 4): v_u_22, (copy 5): v_u_23, (ref 6): v_u_21, (ref 7): v_u_16 ]]
            v_u_19 = nil
            v_u_20:Destroy()
            v_u_24 = nil
            v_u_22:clear()
            v_u_23:clear()
            v_u_21:teardown(p41)
            v_u_16:Destroy()
        end;
        v_u_2:get_base_fn(v15, "create_shine_for_slot_at_cframe")
        v15.create_shine_for_slot_at_cframe = function(_, p42, p43, p44) --[[ Name: create_shine_for_slot_at_cframe ]] --[[ Line: 193 ]]
            --[[ Upvalues: (ref 1): v_u_21 ]]
            v_u_21:create_shine_for_slot_at_cframe(p42, p43, p44)
        end;
        v_u_2:get_base_fn(v15, "game_update")
        v15.game_update = function(_, p45, p46) --[[ Name: game_update ]] --[[ Line: 198 ]]
            --[[ Upvalues: (ref 1): v_u_21, (copy 2): v_u_22, (copy 3): v_u_23 ]]
            v_u_21:update(p45, p46)
            for _, v47 in v_u_22:key_itr() do
                v47:update_obj_cframe(p45)
            end;
            for _, v48 in v_u_23:key_itr() do
                v48:update(p45)
            end;
        end;
        v15.should_do_game_start_zoom_in_effect = function(_) --[[ Name: should_do_game_start_zoom_in_effect ]] --[[ Line: 209 ]]
            return true, 36.5, 28, 0.75;
        end;
        v15.game_camera_transition = function(_, p_u_49) --[[ Name: game_camera_transition ]] --[[ Line: 214 ]]
            --[[ Upvalues: (ref 1): v_u_24, (ref 2): v_u_3, (ref 3): v_u_7 ]]
            if v_u_24 then
                v_u_3:ptry(function() --[[ Line: 216 ]]
                    --[[ Upvalues: (ref 1): v_u_24, (ref 2): v_u_3, (ref 3): v_u_7, (copy 4): p_u_49 ]]
                    v_u_24.Transparency = v_u_3:tra(v_u_7:YForPointOf2PtLineP1P2X(0, 0, 1, 0.4, p_u_49))
                end)
            end;
        end;
        return v15;
    end
};
