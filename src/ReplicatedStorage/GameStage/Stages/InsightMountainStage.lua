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
local v_u_5 = require(game.ReplicatedStorage.Shared.PlayerSettings)
local v_u_6 = require(game.ReplicatedStorage.Shared.BrightnessSettings)
local v_u_7 = require(game.ReplicatedStorage.Shared.ModelLoadDB)
local v_u_8 = require(game.ReplicatedStorage.Shared.ModelLoadDBAsset)
require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.Shared.SPList)
local v_u_9 = nil
local v_u_10 = nil
local v_u_11 = nil
require(game.ReplicatedStorage.Shared.Dependency):require_client(function() --[[ Line: 19 ]]
    --[[ Upvalues: (ref 1): v_u_9, (ref 2): v_u_10, (ref 3): v_u_11 ]]
    v_u_9 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
    v_u_10 = require(game.ReplicatedStorage.GameStage.Util.GameStageDefaultCharacterShineBehaviour)
    v_u_11 = require(game.ReplicatedStorage.Effects.CharacterShineEffect)
end)
return {
    ["new"] = function(_) --[[ Name: new ]] --[[ Line: 27 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_2, (copy 3): v_u_7, (copy 4): v_u_8, (ref 5): v_u_9, (copy 6): v_u_3, (copy 7): v_u_5, (copy 8): v_u_6, (ref 9): v_u_10, (ref 10): v_u_11, (copy 11): v_u_4 ]]
        local v12 = v_u_1:new()
        v_u_2:get_base_fn(v12, "get_name")
        v12.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 31 ]]
            return "Insight Summit";
        end;
        v_u_2:get_base_fn(v12, "get_icon")
        v12.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 33 ]]
            return "rbxassetid://16511148695";
        end;
        local v_u_13 = nil
        v12.load_stage = function(_, p_u_14) --[[ Name: load_stage ]] --[[ Line: 36 ]]
            --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_8, (ref 3): v_u_13 ]]
            v_u_7:singleton():load_model_category(v_u_8.GameStage.InsightMountainStage, v_u_8.Category.GameStage, function(p15) --[[ Line: 37 ]]
                --[[ Upvalues: (ref 1): v_u_13, (copy 2): p_u_14 ]]
                v_u_13 = p15
                p_u_14()
            end)
        end;
        local v_u_16 = nil
        local v_u_17 = nil
        v_u_2:get_base_fn(v12, "setup_stage")
        v12.setup_stage = function(p18, p_u_19) --[[ Name: setup_stage ]] --[[ Line: 48 ]]
            --[[ Upvalues: (ref 1): v_u_13, (ref 2): v_u_9, (ref 3): v_u_16, (ref 4): v_u_3, (ref 5): v_u_5, (ref 6): v_u_6, (ref 7): v_u_17, (ref 8): v_u_10, (ref 9): v_u_11 ]]
            v_u_13.Parent = v_u_9:get_local_elements_folder()
            v_u_9:load_custom_material(v_u_13.InsightMountainStageSnow)
            local v20 = v_u_9:get_game_sky()
            v20.SkyboxBk = "rbxassetid://13412193762"
            v20.SkyboxDn = "rbxassetid://13412195472"
            v20.SkyboxFt = "rbxassetid://13412196774"
            v20.SkyboxLf = "rbxassetid://13412197741"
            v20.SkyboxRt = "rbxassetid://13412198943"
            v20.SkyboxUp = "rbxassetid://13412200693"
            local v21 = v_u_9:get_game_lighting()
            v21.Ambient = Color3.new(0, 0, 0)
            v21.Brightness = 1.2000000476837158
            v21.ColorShift_Bottom = Color3.new(0.470588, 0.129412, 0.764706)
            v21.ColorShift_Top = Color3.new(0.14902, 0, 0.647059)
            v21.OutdoorAmbient = Color3.new(0.498039, 0.498039, 0.498039)
            v21.ClockTime = 11
            v21.GeographicLatitude = 45
            local v22 = v_u_9:get_game_depth_of_field()
            v22.FarIntensity = 0.25
            v22.FocusDistance = 0
            v22.InFocusRadius = 100
            v22.NearIntensity = 0.75
            local v23 = v_u_9:get_game_color_correction()
            v23.Brightness = -0.01
            v23.Contrast = 0.1
            v23.Saturation = 0.01
            v23.TintColor = Color3.fromRGB(235, 247, 255)
            v_u_9:set_game_depth_of_field_enabled(true)
            v_u_9:set_game_color_correction_enabled(true)
            v_u_16 = v_u_13.FaceToPlayer
            v_u_3:ptry(function() --[[ Line: 86 ]]
                --[[ Upvalues: (copy 1): p_u_19, (ref 2): v_u_5, (ref 3): v_u_6, (ref 4): v_u_16 ]]
                if p_u_19._player_settings_manager:get_key(v_u_5.Key.BrightnessSettings) == v_u_6.Normal then
                    v_u_16.NoteGroundPath.Union.Transparency = 0.75
                else
                    v_u_16.NoteGroundPath.Union.Transparency = 0.5
                end;
            end)
            p18:on_switch_focus_slot(p_u_19)
            v_u_17 = v_u_10:new(game.ReplicatedStorage.ElementProtos.CharacterShineEffectProto, v_u_11.CHARACTER_POSITION_OFFSET)
        end;
        v_u_2:get_base_fn(v12, "on_switch_focus_slot")
        v12.on_switch_focus_slot = function(_, p24) --[[ Name: on_switch_focus_slot ]] --[[ Line: 102 ]]
            --[[ Upvalues: (ref 1): v_u_16, (ref 2): v_u_4 ]]
            v_u_16:SetPrimaryPartCFrame(CFrame.new(v_u_4:get_world_center_position(), v_u_4:slot_to_world_position(p24:get_local_game_slot())))
        end;
        v_u_2:get_base_fn(v12, "teardown_stage")
        v12.teardown_stage = function(_, p25) --[[ Name: teardown_stage ]] --[[ Line: 110 ]]
            --[[ Upvalues: (ref 1): v_u_16, (ref 2): v_u_17, (ref 3): v_u_13 ]]
            v_u_16 = nil
            v_u_17:teardown(p25)
            v_u_13:Destroy()
        end;
        v_u_2:get_base_fn(v12, "create_shine_for_slot_at_cframe")
        v12.create_shine_for_slot_at_cframe = function(_, p26, p27, p28) --[[ Name: create_shine_for_slot_at_cframe ]] --[[ Line: 119 ]]
            --[[ Upvalues: (ref 1): v_u_17 ]]
            v_u_17:create_shine_for_slot_at_cframe(p26, p27, p28)
        end;
        v_u_2:get_base_fn(v12, "game_update")
        v12.game_update = function(_, p29, p30) --[[ Name: game_update ]] --[[ Line: 124 ]]
            --[[ Upvalues: (ref 1): v_u_17 ]]
            v_u_17:update(p29, p30)
        end;
        v12.should_do_game_start_zoom_in_effect = function(_) --[[ Name: should_do_game_start_zoom_in_effect ]] --[[ Line: 129 ]]
            return true, 45.625, 24.5, 0.75;
        end;
        return v12;
    end
};
