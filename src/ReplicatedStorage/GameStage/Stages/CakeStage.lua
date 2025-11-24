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
require(game.ReplicatedStorage.Shared.GameSlot)
require(game.ReplicatedStorage.Shared.MatchMode)
require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_6 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_7 = require(game.ReplicatedStorage.PlayerInfo.DanceDatabase)
local v_u_8 = require(game.ReplicatedStorage.Shared.RotatingCFrameObject)
local v_u_9 = require(game.ReplicatedStorage.Shared.ModelLoadDB)
local v_u_10 = require(game.ReplicatedStorage.Shared.ModelLoadDBAsset)
local v_u_11 = nil
local v_u_12 = nil
local v_u_13 = nil
local v_u_14 = nil
require(game.ReplicatedStorage.Shared.Dependency):require_client(function() --[[ Line: 22 ]]
    --[[ Upvalues: (ref 1): v_u_11, (ref 2): v_u_12, (ref 3): v_u_13, (ref 4): v_u_14 ]]
    v_u_11 = require(game.ReplicatedStorage.Shared.BrightnessSettings)
    v_u_12 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
    v_u_13 = require(game.ReplicatedStorage.GameStage.Util.GameStageDefaultCharacterShineBehaviour)
    v_u_14 = require(game.ReplicatedStorage.Effects.CharacterShineEffect)
end)
return {
    ["new"] = function(_) --[[ Name: new ]] --[[ Line: 31 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_2, (copy 3): v_u_9, (copy 4): v_u_10, (ref 5): v_u_12, (ref 6): v_u_13, (copy 7): v_u_5, (copy 8): v_u_6, (copy 9): v_u_3, (copy 10): v_u_7, (copy 11): v_u_8, (copy 12): v_u_4 ]]
        local v15 = v_u_1:new()
        v_u_2:get_base_fn(v15, "get_name")
        v15.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 35 ]]
            return "Make a Cake (and feed the GIANT NOOB!!)";
        end;
        v_u_2:get_base_fn(v15, "get_icon")
        v15.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 37 ]]
            return "rbxassetid://11139367562";
        end;
        local v_u_16 = nil
        v15.load_stage = function(_, p_u_17) --[[ Name: load_stage ]] --[[ Line: 41 ]]
            --[[ Upvalues: (ref 1): v_u_9, (ref 2): v_u_10, (ref 3): v_u_16 ]]
            v_u_9:singleton():load_model_category(v_u_10.GameStage.CakeStage, v_u_10.Category.GameStage, function(p18) --[[ Line: 42 ]]
                --[[ Upvalues: (ref 1): v_u_16, (copy 2): p_u_17 ]]
                v_u_16 = p18
                p_u_17()
            end)
        end;
        local v_u_19 = nil
        local v_u_20 = nil
        local v_u_21 = nil
        local v_u_22 = nil
        local v_u_23 = nil
        local v_u_24 = nil
        v_u_2:get_base_fn(v15, "setup_stage")
        v15.setup_stage = function(p25, p26) --[[ Name: setup_stage ]] --[[ Line: 54 ]]
            --[[ Upvalues: (ref 1): v_u_19, (ref 2): v_u_16, (ref 3): v_u_12, (ref 4): v_u_20, (ref 5): v_u_13, (ref 6): v_u_21, (ref 7): v_u_22, (ref 8): v_u_5, (ref 9): v_u_23, (ref 10): v_u_6, (ref 11): v_u_3, (ref 12): v_u_7, (ref 13): v_u_24, (ref 14): v_u_8, (ref 15): v_u_4 ]]
            v_u_19 = v_u_16.CharacterShineProto
            v_u_19.Parent = nil
            v_u_16.Parent = v_u_12:get_local_elements_folder()
            v_u_20 = v_u_13:new(v_u_19, Vector3.new(0, -3.5, 0))
            v_u_21 = v_u_16.NoobModels
            v_u_22 = v_u_5:new({
                v_u_21.NoobSlot1,
                v_u_21.NoobSlot2,
                v_u_21.NoobSlot3,
                v_u_21.NoobSlot4
            })
            v_u_23 = v_u_6:new({ v_u_16.PlatformNPCs.Chef1.Humanoid, v_u_16.PlatformNPCs.Chef2.Humanoid })
            for _, v_u_27 in v_u_23:key_itr() do
                v_u_3:ptry(function() --[[ Line: 77 ]]
                    --[[ Upvalues: (copy 1): v_u_27, (ref 2): v_u_7, (ref 3): v_u_6 ]]
                    v_u_27:LoadAnimation(v_u_7:singleton():get_dance_animation_for_id(v_u_6:new({
                        3,
                        5,
                        15,
                        217,
                        112,
                        90
                    }):random())):Play()
                end)
            end;
            v_u_24 = v_u_6:new()
            for _, v_u_28 in pairs(v_u_16.RotatingObjects:GetChildren()) do
                v_u_24:push_back(v_u_8:new(v_u_28, nil, function(p29) --[[ Line: 99 ]]
                    --[[ Upvalues: (copy 1): v_u_28 ]]
                    v_u_28.CFrame = p29
                end):set_rotate_time_sec(v_u_3:rand_rangef(10, 20)):set_frame_update_rate(4))
            end;
            p25:on_switch_focus_slot(p26)
            local v30 = v_u_12:get_game_sky()
            v30.SkyboxBk = "rbxassetid://7085965728"
            v30.SkyboxDn = "rbxassetid://7085965728"
            v30.SkyboxFt = "rbxassetid://7085965728"
            v30.SkyboxLf = "rbxassetid://7085965728"
            v30.SkyboxRt = "rbxassetid://7085965728"
            v30.SkyboxUp = "rbxassetid://7085965728"
            local v31 = v_u_12:get_game_lighting()
            v31.Ambient = v_u_4:new(180, 180, 180):to_color3()
            v31.Brightness = 0.25
            v31.ColorShift_Bottom = v_u_4:new(0, 85, 255):to_color3()
            v31.ColorShift_Top = v_u_4:new(184, 194, 255):to_color3()
            v31.OutdoorAmbient = v_u_4:new(0, 85, 255):to_color3()
            v31.ClockTime = 15
            v31.GeographicLatitude = 118
        end;
        v_u_2:get_base_fn(v15, "on_switch_focus_slot")
        v15.on_switch_focus_slot = function(_, p32) --[[ Name: on_switch_focus_slot ]] --[[ Line: 129 ]]
            --[[ Upvalues: (ref 1): v_u_22, (ref 2): v_u_21 ]]
            for v33, v34 in v_u_22:key_itr() do
                if p32:get_local_game_slot() == v33 then
                    v34.Parent = nil
                else
                    v34.Parent = v_u_21
                end;
            end;
        end;
        v_u_2:get_base_fn(v15, "create_shine_for_slot_at_cframe")
        v15.create_shine_for_slot_at_cframe = function(_, p35, p36, p37) --[[ Name: create_shine_for_slot_at_cframe ]] --[[ Line: 140 ]]
            --[[ Upvalues: (ref 1): v_u_20 ]]
            v_u_20:create_shine_for_slot_at_cframe(p35, p36, p37)
        end;
        v_u_2:get_base_fn(v15, "process_character_location_for_slot")
        v15.process_character_location_for_slot = function(_, p38, p39, p40, p41) --[[ Name: process_character_location_for_slot ]] --[[ Line: 145 ]]
            return p38, p39, p40, p41;
        end;
        v_u_2:get_base_fn(v15, "game_update")
        v15.game_update = function(_, p42, p43) --[[ Name: game_update ]] --[[ Line: 150 ]]
            --[[ Upvalues: (ref 1): v_u_20, (ref 2): v_u_24 ]]
            v_u_20:update(p42, p43)
            for _, v44 in v_u_24:key_itr() do
                v44:update_obj_cframe(p42)
            end;
        end;
        v_u_2:get_base_fn(v15, "teardown_stage")
        v15.teardown_stage = function(_, p45) --[[ Name: teardown_stage ]] --[[ Line: 158 ]]
            --[[ Upvalues: (ref 1): v_u_21, (ref 2): v_u_22, (ref 3): v_u_23, (ref 4): v_u_24, (ref 5): v_u_20, (ref 6): v_u_19, (ref 7): v_u_16 ]]
            v_u_21 = nil
            v_u_22 = nil
            v_u_23 = nil
            v_u_24 = nil
            v_u_20:teardown(p45)
            v_u_19:Destroy()
            v_u_16:Destroy()
        end;
        return v15;
    end
};
