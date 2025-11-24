-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:22:08 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.GameStage.StageInfoBase)
local v_u_2 = require(game.ReplicatedStorage.Shared.Override)
require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_3 = require(game.ReplicatedStorage.Shared.GameSlot)
require(game.ReplicatedStorage.Shared.SPVector)
require(game.ReplicatedStorage.Shared.PlayerSettings)
require(game.ReplicatedStorage.Shared.BrightnessSettings)
local v_u_4 = require(game.ReplicatedStorage.Shared.ModelLoadDB)
local v_u_5 = require(game.ReplicatedStorage.Shared.ModelLoadDBAsset)
require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_6 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPDict)
local v_u_7 = require(game.ReplicatedStorage.GameStage.Util.MovingModel)
local v_u_8 = nil
local v_u_9 = nil
local v_u_10 = nil
require(game.ReplicatedStorage.Shared.Dependency):require_client(function() --[[ Line: 21 ]]
    --[[ Upvalues: (ref 1): v_u_8, (ref 2): v_u_9, (ref 3): v_u_10 ]]
    v_u_8 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
    v_u_9 = require(game.ReplicatedStorage.GameStage.Util.GameStageDefaultCharacterShineBehaviour)
    v_u_10 = require(game.ReplicatedStorage.Effects.CharacterShineEffect)
end)
return {
    ["new"] = function(_) --[[ Name: new ]] --[[ Line: 29 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_2, (copy 3): v_u_4, (copy 4): v_u_5, (copy 5): v_u_6, (ref 6): v_u_8, (copy 7): v_u_7, (ref 8): v_u_9, (copy 9): v_u_3 ]]
        local v11 = v_u_1:new()
        v_u_2:get_base_fn(v11, "get_name")
        v11.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 33 ]]
            return "Oceanic Odyssey";
        end;
        v_u_2:get_base_fn(v11, "get_icon")
        v11.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 35 ]]
            return "rbxassetid://17749833775";
        end;
        local v_u_12 = nil
        v11.load_stage = function(_, p_u_13) --[[ Name: load_stage ]] --[[ Line: 38 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_5, (ref 3): v_u_12 ]]
            v_u_4:singleton():load_model_category(v_u_5.GameStage.UnderwaterStage, v_u_5.Category.GameStage, function(p14) --[[ Line: 39 ]]
                --[[ Upvalues: (ref 1): v_u_12, (copy 2): p_u_13 ]]
                v_u_12 = p14
                p_u_13()
            end)
        end;
        local v_u_15 = nil
        local v_u_16 = nil
        local v_u_17 = nil
        local v_u_18 = v_u_6:new()
        v_u_2:get_base_fn(v11, "setup_stage")
        v11.setup_stage = function(p19, p20) --[[ Name: setup_stage ]] --[[ Line: 52 ]]
            --[[ Upvalues: (ref 1): v_u_12, (ref 2): v_u_8, (ref 3): v_u_15, (copy 4): v_u_18, (ref 5): v_u_7, (ref 6): v_u_16, (ref 7): v_u_17, (ref 8): v_u_9 ]]
            v_u_12.Parent = v_u_8:get_local_elements_folder()
            local v21 = v_u_8:get_game_sky()
            v21.SkyboxBk = "rbxassetid://1435962327"
            v21.SkyboxDn = "rbxassetid://1435948462"
            v21.SkyboxFt = "rbxassetid://1435962327"
            v21.SkyboxLf = "rbxassetid://1435943516"
            v21.SkyboxRt = "rbxassetid://1435943516"
            v21.SkyboxUp = "rbxassetid://1435946298"
            local v22 = v_u_8:get_game_lighting()
            v22.Ambient = Color3.new(0.533333, 0.501961, 0.87451)
            v22.Brightness = 0
            v22.ColorShift_Bottom = Color3.new(0.368627, 0.427451, 0.764706)
            v22.ColorShift_Top = Color3.new(0.843137, 0.733333, 1)
            v22.OutdoorAmbient = Color3.new(0.498039, 0.498039, 0.498039)
            v22.ClockTime = 12
            v22.GeographicLatitude = 45
            local v23 = v_u_8:get_game_depth_of_field()
            v23.FarIntensity = 0.25
            v23.FocusDistance = 0
            v23.InFocusRadius = 100
            v23.NearIntensity = 0.75
            local v24 = v_u_8:get_game_color_correction()
            v24.Brightness = 0
            v24.Contrast = 0.1
            v24.Saturation = 0.01
            v24.TintColor = Color3.fromRGB(221, 250, 255)
            v_u_8:set_game_depth_of_field_enabled(true)
            v_u_8:set_game_color_correction_enabled(true)
            v_u_15 = v_u_12
            p19:on_switch_focus_slot(p20)
            for _, v25 in pairs(v_u_15.MovingModels:GetChildren()) do
                v_u_18:push_back(v_u_7:new(v25))
            end;
            v_u_16 = v_u_12.CharacterShineProto
            v_u_16.Parent = nil
            v_u_17 = v_u_9:new(v_u_16, Vector3.new(0, -3.5, 0))
        end;
        v_u_2:get_base_fn(v11, "on_switch_focus_slot")
        v11.on_switch_focus_slot = function(_, p26) --[[ Name: on_switch_focus_slot ]] --[[ Line: 103 ]]
            --[[ Upvalues: (copy 1): v_u_18, (ref 2): v_u_15, (ref 3): v_u_3 ]]
            for _, v27 in v_u_18:key_itr() do
                v27:reset_to_default_position()
            end;
            v_u_15:SetPrimaryPartCFrame(CFrame.new(v_u_3:get_world_center_position(), v_u_3:slot_to_world_position(p26:get_local_game_slot())))
            for _, v28 in v_u_18:key_itr() do
                v28:recalc_positions()
            end;
        end;
        v_u_2:get_base_fn(v11, "teardown_stage")
        v11.teardown_stage = function(_, p29) --[[ Name: teardown_stage ]] --[[ Line: 117 ]]
            --[[ Upvalues: (ref 1): v_u_15, (ref 2): v_u_16, (copy 3): v_u_18, (ref 4): v_u_17, (ref 5): v_u_12 ]]
            v_u_15 = nil
            v_u_16:Destroy()
            v_u_18:clear()
            v_u_17:teardown(p29)
            v_u_12:Destroy()
        end;
        v_u_2:get_base_fn(v11, "create_shine_for_slot_at_cframe")
        v11.create_shine_for_slot_at_cframe = function(_, p30, p31, p32) --[[ Name: create_shine_for_slot_at_cframe ]] --[[ Line: 129 ]]
            --[[ Upvalues: (ref 1): v_u_17 ]]
            v_u_17:create_shine_for_slot_at_cframe(p30, p31, p32)
        end;
        v_u_2:get_base_fn(v11, "game_update")
        v11.game_update = function(_, p33, p34) --[[ Name: game_update ]] --[[ Line: 134 ]]
            --[[ Upvalues: (ref 1): v_u_17, (copy 2): v_u_18 ]]
            v_u_17:update(p33, p34)
            for _, v35 in v_u_18:key_itr() do
                v35:update(p33)
            end;
        end;
        v_u_2:get_base_fn(v11, "should_do_game_start_zoom_in_effect")
        v11.should_do_game_start_zoom_in_effect = function(_) --[[ Name: should_do_game_start_zoom_in_effect ]] --[[ Line: 142 ]]
            return true, 45.625, 24.5, 0.75;
        end;
        return v11;
    end
};
