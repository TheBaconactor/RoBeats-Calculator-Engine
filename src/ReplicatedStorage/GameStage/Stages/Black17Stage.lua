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
local v_u_5 = require(game.ReplicatedStorage.Shared.SPVector)
require(game.ReplicatedStorage.Shared.PlayerSettings)
require(game.ReplicatedStorage.Shared.BrightnessSettings)
local v_u_6 = require(game.ReplicatedStorage.Shared.ModelLoadDB)
local v_u_7 = require(game.ReplicatedStorage.Shared.ModelLoadDBAsset)
local v_u_8 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_9 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_10 = require(game.ReplicatedStorage.Shared.RotatingCFrameObject)
local v_u_11 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_12 = nil
local v_u_13 = nil
local v_u_14 = nil
require(game.ReplicatedStorage.Shared.Dependency):require_client(function() --[[ Line: 21 ]]
    --[[ Upvalues: (ref 1): v_u_12, (ref 2): v_u_13, (ref 3): v_u_14 ]]
    v_u_12 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
    v_u_13 = require(game.ReplicatedStorage.GameStage.Util.GameStageDefaultCharacterShineBehaviour)
    v_u_14 = require(game.ReplicatedStorage.Effects.CharacterShineEffect)
end)
return {
    ["new"] = function(_) --[[ Name: new ]] --[[ Line: 29 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_2, (copy 3): v_u_6, (copy 4): v_u_7, (copy 5): v_u_9, (ref 6): v_u_12, (copy 7): v_u_5, (ref 8): v_u_13, (copy 9): v_u_11, (copy 10): v_u_8, (copy 11): v_u_3, (copy 12): v_u_10, (copy 13): v_u_4 ]]
        local v15 = v_u_1:new()
        v_u_2:get_base_fn(v15, "get_name")
        v15.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 33 ]]
            return "Black Phonk-alypse!";
        end;
        v_u_2:get_base_fn(v15, "get_icon")
        v15.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 35 ]]
            return "rbxassetid://112563679906944";
        end;
        local v_u_16 = nil
        v15.load_stage = function(_, p_u_17) --[[ Name: load_stage ]] --[[ Line: 38 ]]
            --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_7, (ref 3): v_u_16 ]]
            v_u_6:singleton():load_model_category(v_u_7.GameStage.Black17Stage, v_u_7.Category.GameStage, function(p18) --[[ Line: 39 ]]
                --[[ Upvalues: (ref 1): v_u_16, (copy 2): p_u_17 ]]
                v_u_16 = p18
                p_u_17()
            end)
        end;
        local v_u_19 = nil
        local v_u_20 = nil
        local v_u_21 = nil
        local v_u_22 = v_u_9:new()
        v_u_2:get_base_fn(v15, "setup_stage")
        v15.setup_stage = function(p23, p24) --[[ Name: setup_stage ]] --[[ Line: 53 ]]
            --[[ Upvalues: (ref 1): v_u_16, (ref 2): v_u_12, (ref 3): v_u_5, (ref 4): v_u_19, (ref 5): v_u_20, (ref 6): v_u_21, (ref 7): v_u_13, (ref 8): v_u_11, (ref 9): v_u_8, (ref 10): v_u_3, (copy 11): v_u_22, (ref 12): v_u_10, (ref 13): v_u_9 ]]
            v_u_16.Parent = v_u_12:get_local_elements_folder()
            local v25 = v_u_12:get_game_sky()
            v25.SkyboxBk = "rbxassetid://14042163127"
            v25.SkyboxDn = "rbxassetid://14042167610"
            v25.SkyboxFt = "rbxassetid://14042168960"
            v25.SkyboxLf = "rbxassetid://14042170362"
            v25.SkyboxRt = "rbxassetid://14042171912"
            v25.SkyboxUp = "rbxassetid://14042172947"
            local v26 = v_u_12:get_game_lighting()
            v26.Ambient = Color3.new(0.517647, 0.427451, 0.0980392)
            v26.Brightness = 1
            v26.ColorShift_Bottom = Color3.new(0.470588, 0.129412, 0.764706)
            v26.ColorShift_Top = Color3.new(0.14902, 0, 0.647059)
            v26.OutdoorAmbient = Color3.new(0.498039, 0.498039, 0.498039)
            v26.ClockTime = 12
            v26.GeographicLatitude = 45
            local v27 = v_u_12:get_game_atmosphere()
            v27.Density = 0.3
            v27.Offset = 0.25
            v27.Glare = 0
            v27.Haze = 0
            v27.Color = v_u_5:new(199, 199, 199):to_color3()
            v27.Decay = v_u_5:new(106, 112, 125):to_color3()
            v_u_12:set_game_atmosphere_enabled(true)
            v_u_19 = v_u_16.FaceToPlayer
            p23:on_switch_focus_slot(p24)
            v_u_20 = v_u_16.CharacterShineProto
            v_u_20.Parent = nil
            v_u_21 = v_u_13:new(v_u_20, Vector3.new(0, -3.5, 0))
            local v28 = v_u_11:singleton():get_difficulty_for_key(p24:es_gamelocal_get_audiomanager():get_song_key())
            local v_u_29 = v_u_8:YForPointOf2PtLineP1P2X(5, 210, 30, 105, v_u_3:clamp(v28, 5, 30))
            local v30 = v_u_8:YForPointOf2PtLineP1P2X(5, 390, 30, 195, v_u_3:clamp(v28, 5, 30))
            v_u_22:clear()
            v_u_22:push_back(v_u_10:new(v_u_16.Clouds.LevelClouds1):set_rotation_axis(Vector3.new(0, 1, 0)):set_rotate_time_sec(v_u_29))
            v_u_22:push_back(v_u_10:new(v_u_16.Clouds.LevelClouds2):set_rotation_axis(Vector3.new(0, -1, 0)):set_rotate_time_sec(v30))
            v_u_22:push_back(v_u_10:new(v_u_16.FaceToPlayer.CloudCenter.CloudBase):set_rotation_axis(Vector3.new(0, 1, 0)):set_rotate_time_sec(v_u_29 * 0.31))
            v_u_22:push_back(v_u_10:new(v_u_16.FaceToPlayer.CloudCenter.CloudSpiral):set_rotation_axis(Vector3.new(0, -1, 0)):set_rotate_time_sec(v_u_29 * 0.311))
            v_u_22:push_back(v_u_10:new(v_u_16.FaceToPlayer.CloudCenter.CloudFire1):set_rotation_axis(Vector3.new(0, 1, 0)):set_rotate_time_sec(v_u_29 * 0.312))
            v_u_22:push_back(v_u_10:new(v_u_16.FaceToPlayer.CloudCenter.CloudFire2):set_rotation_axis(Vector3.new(0, -1, 0)):set_rotate_time_sec(v_u_29 * 0.313))
            v_u_9:for_each(v_u_9:new({
                v_u_16.FaceToPlayer.Fire1,
                v_u_16.FaceToPlayer.Fire2,
                v_u_16.FaceToPlayer.Fire3,
                v_u_16.FaceToPlayer.Fire4,
                v_u_16.FaceToPlayer.FireTest
            }), function(p_u_31) --[[ Line: 136 ]]
                --[[ Upvalues: (ref 1): v_u_3, (copy 2): v_u_29, (ref 3): v_u_22, (ref 4): v_u_10, (ref 5): v_u_8 ]]
                local v_u_32 = v_u_3:get_list_of_children_of_classname(p_u_31, "MeshPart")
                for v33 = 1, v_u_32:count() do
                    v_u_32:get(v33).Transparency = v_u_3:tra(0)
                end;
                v_u_22:push_back(v_u_10:new(p_u_31, function() --[[ Line: 145 ]]
                    return CFrame.new();
                end, function(_, _, _, _, _, _, _, _, p34) --[[ Line: 148 ]]
                    --[[ Upvalues: (copy 1): p_u_31, (ref 2): v_u_8, (copy 3): v_u_32, (ref 4): v_u_3 ]]
                    p_u_31:ScaleTo(v_u_8:YForPointOf2PtLineP1P2X(0, 0.1, 1, 0.75, p34))
                    for v35 = 1, v_u_32:count() do
                        v_u_32:get(v35).Transparency = v_u_8:YForPointOf2PtLineP1P2X(0, v_u_3:tra(1), 1, v_u_3:tra(0), p34)
                    end;
                end):set_rotate_time_sec(v_u_29 * 0.01 + v_u_3:rand_rangef(0, 1)))
            end)
            local v36 = v_u_9:new()
            v36:push_back_from_list(v_u_3:get_list_of_children_of_classname(v_u_16.FaceToPlayer.Car1, "ImageLabel"))
            v36:push_back_from_list(v_u_3:get_list_of_children_of_classname(v_u_16.FaceToPlayer.Car2, "ImageLabel"))
            v_u_9:for_each(v36, function(p_u_37) --[[ Line: 164 ]]
                --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_8, (copy 3): v_u_29, (ref 4): v_u_22, (ref 5): v_u_10 ]]
                local v_u_38 = v_u_3:rand_rangef(0, 3.14)
                local function _(p39) --[[ Name: image_transparency_for_angle ]] --[[ Line: 167 ]]
                    --[[ Upvalues: (ref 1): v_u_3, (copy 2): v_u_38, (ref 3): v_u_8 ]]
                    return v_u_8:YForPointOf2PtLineP1P2X(0, 0.45, 1, 0.65, (v_u_3:tra((math.sin(p39 + v_u_38) + 1) / 2)));
                end;
                p_u_37.ImageTransparency = v_u_8:YForPointOf2PtLineP1P2X(0, 0.45, 1, 0.65, (v_u_3:tra((math.sin(0 + v_u_38) + 1) / 2)))
                v_u_22:push_back(v_u_10:new(nil, function() --[[ Line: 177 ]]
                    return CFrame.new();
                end, function(_, _, _, _, _, p40, _, _, _) --[[ Line: 180 ]]
                    --[[ Upvalues: (copy 1): p_u_37, (ref 2): v_u_3, (copy 3): v_u_38, (ref 4): v_u_8 ]]
                    p_u_37.ImageTransparency = v_u_8:YForPointOf2PtLineP1P2X(0, 0.45, 1, 0.65, (v_u_3:tra((math.sin(p40 + v_u_38) + 1) / 2)))
                end):set_rotate_time_sec(v_u_29 * 0.01 * 0.5 + v_u_3:rand_rangef(0, 0.05)))
            end)
        end;
        v_u_2:get_base_fn(v15, "on_switch_focus_slot")
        v15.on_switch_focus_slot = function(_, p41) --[[ Name: on_switch_focus_slot ]] --[[ Line: 192 ]]
            --[[ Upvalues: (ref 1): v_u_19, (ref 2): v_u_4 ]]
            v_u_19:SetPrimaryPartCFrame(CFrame.new(v_u_4:get_world_center_position(), v_u_4:slot_to_world_position(p41:get_local_game_slot())))
        end;
        v_u_2:get_base_fn(v15, "teardown_stage")
        v15.teardown_stage = function(_, p42) --[[ Name: teardown_stage ]] --[[ Line: 200 ]]
            --[[ Upvalues: (ref 1): v_u_19, (ref 2): v_u_20, (copy 3): v_u_22, (ref 4): v_u_21, (ref 5): v_u_16 ]]
            v_u_19 = nil
            v_u_20:Destroy()
            v_u_22:clear()
            v_u_21:teardown(p42)
            v_u_16:Destroy()
        end;
        v_u_2:get_base_fn(v15, "create_shine_for_slot_at_cframe")
        v15.create_shine_for_slot_at_cframe = function(_, p43, p44, p45) --[[ Name: create_shine_for_slot_at_cframe ]] --[[ Line: 211 ]]
            --[[ Upvalues: (ref 1): v_u_21 ]]
            v_u_21:create_shine_for_slot_at_cframe(p43, p44, p45)
        end;
        v_u_2:get_base_fn(v15, "game_update")
        v15.game_update = function(_, p46, p47) --[[ Name: game_update ]] --[[ Line: 216 ]]
            --[[ Upvalues: (ref 1): v_u_21, (copy 2): v_u_22 ]]
            v_u_21:update(p46, p47)
            for v48 = 1, v_u_22:count() do
                v_u_22:get(v48):update_obj_cframe(p46)
            end;
        end;
        v_u_2:get_base_fn(v15, "should_do_game_start_zoom_in_effect")
        v15.should_do_game_start_zoom_in_effect = function(_) --[[ Name: should_do_game_start_zoom_in_effect ]] --[[ Line: 224 ]]
            return true, 45.625, 24.5, 0.75;
        end;
        return v15;
    end
};
