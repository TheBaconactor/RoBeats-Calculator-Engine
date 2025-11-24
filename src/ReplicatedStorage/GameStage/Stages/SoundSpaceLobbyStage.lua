-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:22:07 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.GameStage.StageInfoBase)
local v_u_2 = require(game.ReplicatedStorage.Shared.Override)
require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPVector)
require(game.ReplicatedStorage.Shared.GameSlot)
require(game.ReplicatedStorage.Shared.MatchMode)
require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.PlayerInfo.DanceDatabase)
require(game.ReplicatedStorage.Shared.RotatingCFrameObject)
local v_u_5 = require(game.ReplicatedStorage.Shared.ModelLoadDB)
local v_u_6 = require(game.ReplicatedStorage.Shared.ModelLoadDBAsset)
local v_u_7 = nil
local v_u_8 = nil
local v_u_9 = nil
local v_u_10 = nil
require(game.ReplicatedStorage.Shared.Dependency):require_client(function() --[[ Line: 22 ]]
    --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_8, (ref 3): v_u_9, (ref 4): v_u_10 ]]
    v_u_7 = require(game.ReplicatedStorage.Shared.BrightnessSettings)
    v_u_8 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
    v_u_9 = require(game.ReplicatedStorage.GameStage.Util.GameStageDefaultCharacterShineBehaviour)
    v_u_10 = require(game.ReplicatedStorage.Effects.CharacterShineEffect)
end)
return {
    ["new"] = function(_) --[[ Name: new ]] --[[ Line: 31 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_2, (copy 3): v_u_5, (copy 4): v_u_6, (ref 5): v_u_8, (ref 6): v_u_9, (copy 7): v_u_4, (copy 8): v_u_3 ]]
        local v11 = v_u_1:new()
        v_u_2:get_base_fn(v11, "get_name")
        v11.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 35 ]]
            return "Sound Space Arcade";
        end;
        v_u_2:get_base_fn(v11, "get_icon")
        v11.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 37 ]]
            return "rbxassetid://11141006311";
        end;
        local v_u_12 = nil
        v11.load_stage = function(_, p_u_13) --[[ Name: load_stage ]] --[[ Line: 40 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_6, (ref 3): v_u_12 ]]
            v_u_5:singleton():load_model_category(v_u_6.GameStage.SoundSpaceStage, v_u_6.Category.GameStage, function(p14) --[[ Line: 41 ]]
                --[[ Upvalues: (ref 1): v_u_12, (copy 2): p_u_13 ]]
                v_u_12 = p14
                p_u_13()
            end)
        end;
        local v_u_15 = nil
        local v_u_16 = nil
        local v_u_17 = nil
        local v_u_18 = nil
        v_u_2:get_base_fn(v11, "setup_stage")
        v11.setup_stage = function(p19, p20) --[[ Name: setup_stage ]] --[[ Line: 51 ]]
            --[[ Upvalues: (ref 1): v_u_15, (ref 2): v_u_12, (ref 3): v_u_8, (ref 4): v_u_16, (ref 5): v_u_9, (ref 6): v_u_17, (ref 7): v_u_18, (ref 8): v_u_4, (ref 9): v_u_3 ]]
            v_u_15 = v_u_12.CharacterShineProto
            v_u_15.Parent = nil
            v_u_12.Parent = v_u_8:get_local_elements_folder()
            v_u_16 = v_u_9:new(v_u_15, Vector3.new(0, -3.5, 0))
            v_u_17 = v_u_12.Machines
            v_u_18 = v_u_4:new({
                v_u_17.MachineSlot1,
                v_u_17.MachineSlot2,
                v_u_17.MachineSlot3,
                v_u_17.MachineSlot4
            })
            p19:on_switch_focus_slot(p20)
            local v21 = v_u_8:get_game_lighting()
            v21.Ambient = v_u_3:new(0, 0, 0):to_color3()
            v21.Brightness = 1
            v21.ColorShift_Bottom = v_u_3:new(120, 33, 195):to_color3()
            v21.ColorShift_Top = v_u_3:new(38, 0, 165):to_color3()
            v21.OutdoorAmbient = v_u_3:new(127, 127, 127):to_color3()
            v21.ClockTime = 12
            v21.GeographicLatitude = 45
        end;
        v_u_2:get_base_fn(v11, "on_switch_focus_slot")
        v11.on_switch_focus_slot = function(_, p22) --[[ Name: on_switch_focus_slot ]] --[[ Line: 82 ]]
            --[[ Upvalues: (ref 1): v_u_18, (ref 2): v_u_17 ]]
            for v23, v24 in v_u_18:key_itr() do
                if p22:get_local_game_slot() == v23 then
                    v24.Parent = nil
                else
                    v24.Parent = v_u_17
                end;
            end;
        end;
        v_u_2:get_base_fn(v11, "create_shine_for_slot_at_cframe")
        v11.create_shine_for_slot_at_cframe = function(_, p25, p26, p27) --[[ Name: create_shine_for_slot_at_cframe ]] --[[ Line: 93 ]]
            --[[ Upvalues: (ref 1): v_u_16 ]]
            v_u_16:create_shine_for_slot_at_cframe(p25, p26, p27)
        end;
        v_u_2:get_base_fn(v11, "process_character_location_for_slot")
        v11.process_character_location_for_slot = function(_, p28, p29, p30, p31) --[[ Name: process_character_location_for_slot ]] --[[ Line: 98 ]]
            return p28, p29, p30, p31;
        end;
        v_u_2:get_base_fn(v11, "game_update")
        v11.game_update = function(_, p32, p33) --[[ Name: game_update ]] --[[ Line: 103 ]]
            --[[ Upvalues: (ref 1): v_u_16 ]]
            v_u_16:update(p32, p33)
        end;
        v_u_2:get_base_fn(v11, "teardown_stage")
        v11.teardown_stage = function(_, p34) --[[ Name: teardown_stage ]] --[[ Line: 108 ]]
            --[[ Upvalues: (ref 1): v_u_17, (ref 2): v_u_18, (ref 3): v_u_16, (ref 4): v_u_15, (ref 5): v_u_12 ]]
            v_u_17 = nil
            v_u_18 = nil
            v_u_16:teardown(p34)
            v_u_15:Destroy()
            v_u_12:Destroy()
        end;
        v_u_2:get_base_fn(v11, "should_do_game_start_zoom_in_effect")
        v11.should_do_game_start_zoom_in_effect = function(_) --[[ Name: should_do_game_start_zoom_in_effect ]] --[[ Line: 117 ]]
            return true, 18.25, 14, 0.75;
        end;
        return v11;
    end
};
