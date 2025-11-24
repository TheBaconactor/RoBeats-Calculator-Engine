-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:22:07 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.GameStage.StageInfoBase)
local v_u_2 = require(game.ReplicatedStorage.Shared.Override)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPVector)
local v_u_5 = require(game.ReplicatedStorage.Shared.GameSlot)
require(game.ReplicatedStorage.Shared.MatchMode)
local v_u_6 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_7 = require(game.ReplicatedStorage.Shared.ModelLoadDB)
local v_u_8 = require(game.ReplicatedStorage.Shared.ModelLoadDBAsset)
local v_u_9 = nil
local v_u_10 = nil
local v_u_11 = nil
local v_u_12 = nil
require(game.ReplicatedStorage.Shared.Dependency):require_client(function() --[[ Line: 18 ]]
    --[[ Upvalues: (ref 1): v_u_9, (ref 2): v_u_10, (ref 3): v_u_11, (ref 4): v_u_12 ]]
    v_u_9 = require(game.ReplicatedStorage.Shared.BrightnessSettings)
    v_u_10 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
    v_u_11 = require(game.ReplicatedStorage.GameStage.Util.GameStageDefaultCharacterShineBehaviour)
    v_u_12 = require(game.ReplicatedStorage.Effects.CharacterShineEffect)
end)
return {
    ["new"] = function(_) --[[ Name: new ]] --[[ Line: 27 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_2, (copy 3): v_u_7, (copy 4): v_u_8, (ref 5): v_u_10, (ref 6): v_u_11, (copy 7): v_u_4, (copy 8): v_u_5, (copy 9): v_u_6, (copy 10): v_u_3 ]]
        local v13 = v_u_1:new()
        v_u_2:get_base_fn(v13, "get_name")
        v13.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 31 ]]
            return "Lonely Little Star";
        end;
        v_u_2:get_base_fn(v13, "get_icon")
        v13.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 33 ]]
            return "rbxassetid://10677399571";
        end;
        local v_u_14 = nil
        v13.load_stage = function(_, p_u_15) --[[ Name: load_stage ]] --[[ Line: 36 ]]
            --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_8, (ref 3): v_u_14 ]]
            v_u_7:singleton():load_model_category(v_u_8.GameStage.LonelyLittlePlanetStage, v_u_8.Category.GameStage, function(p16) --[[ Line: 37 ]]
                --[[ Upvalues: (ref 1): v_u_14, (copy 2): p_u_15 ]]
                v_u_14 = p16
                p_u_15()
            end)
        end;
        local v_u_17 = nil
        local v_u_18 = nil
        local v_u_19 = nil
        local v_u_20 = nil
        local v_u_21 = nil
        local v_u_22 = nil
        local v_u_23 = 0
        local v_u_24 = 0
        local v_u_25 = 0
        v_u_2:get_base_fn(v13, "setup_stage")
        v13.setup_stage = function(p26, p27) --[[ Name: setup_stage ]] --[[ Line: 56 ]]
            --[[ Upvalues: (ref 1): v_u_17, (ref 2): v_u_14, (ref 3): v_u_10, (ref 4): v_u_18, (ref 5): v_u_11, (ref 6): v_u_20, (ref 7): v_u_23, (ref 8): v_u_21, (ref 9): v_u_24, (ref 10): v_u_22, (ref 11): v_u_25, (ref 12): v_u_19, (ref 13): v_u_4 ]]
            v_u_17 = v_u_14.CharacterShineProto
            v_u_17.Parent = nil
            v_u_10:get_game_lighting().ClockTime = 0
            v_u_14.Parent = v_u_10:get_local_elements_folder()
            v_u_18 = v_u_11:new(v_u_17, Vector3.new(0, -3.5, 0))
            v_u_20 = v_u_14.Planets
            v_u_23 = 0
            v_u_21 = v_u_14.StagePlanet
            v_u_24 = 0
            v_u_22 = v_u_14.FaceToPlayer.AlienShip.ShipLight
            v_u_25 = 0
            v_u_19 = v_u_14.FaceToPlayer
            p26:on_switch_focus_slot(p27)
            local v28 = v_u_10:get_game_sky()
            v28.SkyboxBk = "rbxassetid://10163039183"
            v28.SkyboxDn = "rbxassetid://10163039183"
            v28.SkyboxFt = "rbxassetid://10163039183"
            v28.SkyboxLf = "rbxassetid://10163039183"
            v28.SkyboxRt = "rbxassetid://10163039183"
            v28.SkyboxUp = "rbxassetid://10163039183"
            local v29 = v_u_10:get_game_lighting()
            v29.Ambient = v_u_4:new(138, 158, 248):to_color3()
            v29.Brightness = 0.05
            v29.ColorShift_Bottom = v_u_4:new(153, 203, 236):to_color3()
            v29.ColorShift_Top = v_u_4:new(0, 30, 165):to_color3()
            v29.OutdoorAmbient = v_u_4:new(127, 127, 127):to_color3()
            v29.ClockTime = 12
            v29.GeographicLatitude = 45
            local v30 = v_u_10:get_game_atmosphere()
            v30.Density = 0.3
            v30.Offset = 0.25
            v30.Glare = 0
            v30.Haze = 0
            v30.Color = v_u_4:new(199, 199, 199):to_color3()
            v30.Decay = v_u_4:new(106, 112, 125):to_color3()
            v_u_10:set_game_atmosphere_enabled(true)
        end;
        v_u_2:get_base_fn(v13, "on_switch_focus_slot")
        v13.on_switch_focus_slot = function(_, p31) --[[ Name: on_switch_focus_slot ]] --[[ Line: 108 ]]
            --[[ Upvalues: (ref 1): v_u_19, (ref 2): v_u_5 ]]
            v_u_19:SetPrimaryPartCFrame(CFrame.new(v_u_5:get_world_center_position(), v_u_5:slot_to_world_position(p31:get_local_game_slot())))
        end;
        v_u_2:get_base_fn(v13, "create_shine_for_slot_at_cframe")
        v13.create_shine_for_slot_at_cframe = function(_, p32, p33, p34) --[[ Name: create_shine_for_slot_at_cframe ]] --[[ Line: 116 ]]
            --[[ Upvalues: (ref 1): v_u_18 ]]
            v_u_18:create_shine_for_slot_at_cframe(p32, p33, p34)
        end;
        v_u_2:get_base_fn(v13, "game_update")
        v13.game_update = function(_, p35, p36) --[[ Name: game_update ]] --[[ Line: 121 ]]
            --[[ Upvalues: (ref 1): v_u_18, (ref 2): v_u_23, (ref 3): v_u_6, (ref 4): v_u_20, (ref 5): v_u_24, (ref 6): v_u_21, (ref 7): v_u_25, (ref 8): v_u_22, (ref 9): v_u_3 ]]
            v_u_18:update(p35, p36)
            v_u_23 = v_u_6:IncrementWrap(v_u_23, v_u_6:SecondsToTick(300) * p35, 1)
            v_u_20:SetPrimaryPartCFrame(CFrame.new(v_u_20.PrimaryPart.Position) * CFrame.Angles(0, v_u_23 * 3.141592653589793 * 2, 0))
            v_u_24 = v_u_6:IncrementWrap(v_u_24, v_u_6:SecondsToTick(351) * p35, 1)
            v_u_21:SetPrimaryPartCFrame(CFrame.new(v_u_21.PrimaryPart.Position) * CFrame.Angles(0, 0, v_u_24 * 3.141592653589793 * 2))
            if p36:es_gamelocal_get_audiomanager():is_beat() then
                v_u_25 = 0.12
            else
                v_u_25 = v_u_6:expt_sec(v_u_25, 0.1, 1, p35)
            end;
            v_u_22.Transparency = v_u_3:tra(v_u_25)
        end;
        v_u_2:get_base_fn(v13, "teardown_stage")
        v13.teardown_stage = function(_, p37) --[[ Name: teardown_stage ]] --[[ Line: 151 ]]
            --[[ Upvalues: (ref 1): v_u_20, (ref 2): v_u_21, (ref 3): v_u_22, (ref 4): v_u_18, (ref 5): v_u_17, (ref 6): v_u_19, (ref 7): v_u_14 ]]
            v_u_20 = nil
            v_u_21 = nil
            v_u_22 = nil
            v_u_18:teardown(p37)
            v_u_17:Destroy()
            v_u_19:Destroy()
            v_u_14:Destroy()
        end;
        v_u_2:get_base_fn(v13, "should_do_game_start_zoom_in_effect")
        v13.should_do_game_start_zoom_in_effect = function(_) --[[ Name: should_do_game_start_zoom_in_effect ]] --[[ Line: 162 ]]
            return true, 49.275000000000006, 18.900000000000002, 0.75;
        end;
        return v13;
    end
};
