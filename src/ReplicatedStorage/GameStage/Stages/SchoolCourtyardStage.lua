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
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_2, (copy 3): v_u_7, (copy 4): v_u_8, (ref 5): v_u_9, (copy 6): v_u_3, (copy 7): v_u_5, (copy 8): v_u_6, (ref 9): v_u_10, (copy 10): v_u_4 ]]
        local v12 = v_u_1:new()
        v_u_2:get_base_fn(v12, "get_name")
        v12.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 31 ]]
            return "School-Year Sentiments";
        end;
        v_u_2:get_base_fn(v12, "get_icon")
        v12.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 33 ]]
            return "rbxassetid://16512206298";
        end;
        local v_u_13 = nil
        v12.load_stage = function(_, p_u_14) --[[ Name: load_stage ]] --[[ Line: 36 ]]
            --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_8, (ref 3): v_u_13 ]]
            v_u_7:singleton():load_model_category(v_u_8.GameStage.SchoolCourtyardStage, v_u_8.Category.GameStage, function(p15) --[[ Line: 37 ]]
                --[[ Upvalues: (ref 1): v_u_13, (copy 2): p_u_14 ]]
                v_u_13 = p15
                p_u_14()
            end)
        end;
        local v_u_16 = nil
        local v_u_17 = nil
        local v_u_18 = nil
        v_u_2:get_base_fn(v12, "setup_stage")
        v12.setup_stage = function(p19, p_u_20) --[[ Name: setup_stage ]] --[[ Line: 48 ]]
            --[[ Upvalues: (ref 1): v_u_13, (ref 2): v_u_9, (ref 3): v_u_16, (ref 4): v_u_3, (ref 5): v_u_5, (ref 6): v_u_6, (ref 7): v_u_17, (ref 8): v_u_18, (ref 9): v_u_10 ]]
            v_u_13.Parent = v_u_9:get_local_elements_folder()
            local v21 = v_u_9:get_game_sky()
            v21.SkyboxBk = "rbxassetid://13107325341"
            v21.SkyboxDn = "rbxassetid://13107329809"
            v21.SkyboxFt = "rbxassetid://13107334845"
            v21.SkyboxLf = "rbxassetid://13107337703"
            v21.SkyboxRt = "rbxassetid://13107340396"
            v21.SkyboxUp = "rbxassetid://15320777875"
            local v22 = v_u_9:get_game_lighting()
            v22.Ambient = Color3.new(0, 0, 0)
            v22.Brightness = 1
            v22.ColorShift_Bottom = Color3.new(0.470588, 0.129412, 0.764706)
            v22.ColorShift_Top = Color3.new(0.14902, 0, 0.647059)
            v22.OutdoorAmbient = Color3.new(0.498039, 0.498039, 0.498039)
            v22.ClockTime = 14.300000190734863
            v22.GeographicLatitude = 45
            v_u_16 = v_u_13.FaceToPlayer
            v_u_3:ptry(function() --[[ Line: 69 ]]
                --[[ Upvalues: (copy 1): p_u_20, (ref 2): v_u_5, (ref 3): v_u_6, (ref 4): v_u_16 ]]
                if p_u_20._player_settings_manager:get_key(v_u_5.Key.BrightnessSettings) == v_u_6.Normal then
                    v_u_16.BGDecorations.TrackPlatform.Union.Transparency = 1
                else
                    v_u_16.BGDecorations.TrackPlatform.Union.Transparency = 0.45
                end;
            end)
            p19:on_switch_focus_slot(p_u_20)
            v_u_17 = v_u_13.CharacterShineProto
            v_u_17.Parent = nil
            v_u_18 = v_u_10:new(v_u_17, Vector3.new(0, -3.5, 0))
        end;
        v_u_2:get_base_fn(v12, "on_switch_focus_slot")
        v12.on_switch_focus_slot = function(_, p23) --[[ Name: on_switch_focus_slot ]] --[[ Line: 87 ]]
            --[[ Upvalues: (ref 1): v_u_16, (ref 2): v_u_4 ]]
            v_u_16:SetPrimaryPartCFrame(CFrame.new(v_u_4:get_world_center_position(), v_u_4:slot_to_world_position(p23:get_local_game_slot())))
        end;
        v_u_2:get_base_fn(v12, "teardown_stage")
        v12.teardown_stage = function(_, p24) --[[ Name: teardown_stage ]] --[[ Line: 95 ]]
            --[[ Upvalues: (ref 1): v_u_16, (ref 2): v_u_17, (ref 3): v_u_18, (ref 4): v_u_13 ]]
            v_u_16 = nil
            v_u_17:Destroy()
            v_u_18:teardown(p24)
            v_u_13:Destroy()
        end;
        v_u_2:get_base_fn(v12, "create_shine_for_slot_at_cframe")
        v12.create_shine_for_slot_at_cframe = function(_, p25, p26, p27) --[[ Name: create_shine_for_slot_at_cframe ]] --[[ Line: 105 ]]
            --[[ Upvalues: (ref 1): v_u_18 ]]
            v_u_18:create_shine_for_slot_at_cframe(p25, p26, p27)
        end;
        v_u_2:get_base_fn(v12, "game_update")
        v12.game_update = function(_, p28, p29) --[[ Name: game_update ]] --[[ Line: 110 ]]
            --[[ Upvalues: (ref 1): v_u_18 ]]
            v_u_18:update(p28, p29)
        end;
        v12.should_do_game_start_zoom_in_effect = function(_) --[[ Name: should_do_game_start_zoom_in_effect ]] --[[ Line: 115 ]]
            return true, 52.5, 25.5, 0.9375;
        end;
        return v12;
    end
};
