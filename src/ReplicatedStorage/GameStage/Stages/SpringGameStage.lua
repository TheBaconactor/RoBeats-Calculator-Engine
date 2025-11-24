-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:22:06 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.GameStage.StageInfoBase)
local v_u_2 = require(game.ReplicatedStorage.Shared.Override)
require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_3 = require(game.ReplicatedStorage.Shared.GameSlot)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPVector)
local v_u_5 = require(game.ReplicatedStorage.Shared.PlayerSettings)
local v_u_6 = require(game.ReplicatedStorage.Shared.BrightnessSettings)
local v_u_7 = require(game.ReplicatedStorage.Shared.ModelLoadDB)
local v_u_8 = require(game.ReplicatedStorage.Shared.ModelLoadDBAsset)
local v_u_9 = nil
local v_u_10 = nil
local v_u_11 = nil
require(game.ReplicatedStorage.Shared.Dependency):require_client(function() --[[ Line: 17 ]]
    --[[ Upvalues: (ref 1): v_u_9, (ref 2): v_u_10, (ref 3): v_u_11 ]]
    v_u_9 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
    v_u_10 = require(game.ReplicatedStorage.GameStage.Util.GameStageDefaultCharacterShineBehaviour)
    v_u_11 = require(game.ReplicatedStorage.Effects.CharacterShineEffect)
end)
return {
    ["new"] = function(_) --[[ Name: new ]] --[[ Line: 25 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_2, (copy 3): v_u_7, (copy 4): v_u_8, (ref 5): v_u_9, (copy 6): v_u_5, (copy 7): v_u_6, (copy 8): v_u_4, (ref 9): v_u_10, (ref 10): v_u_11, (copy 11): v_u_3 ]]
        local v12 = v_u_1:new()
        v_u_2:get_base_fn(v12, "get_name")
        v12.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 29 ]]
            return "Spring Cherry Blossoms";
        end;
        v_u_2:get_base_fn(v12, "get_icon")
        v12.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 31 ]]
            return "http://www.roblox.com/asset/?id=9470049599";
        end;
        local v_u_13 = nil
        v12.load_stage = function(_, p_u_14) --[[ Name: load_stage ]] --[[ Line: 34 ]]
            --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_8, (ref 3): v_u_13 ]]
            v_u_7:singleton():load_model_category(v_u_8.GameStage.SpringStage, v_u_8.Category.GameStage, function(p15) --[[ Line: 35 ]]
                --[[ Upvalues: (ref 1): v_u_13, (copy 2): p_u_14 ]]
                v_u_13 = p15
                p_u_14()
            end)
        end;
        local v_u_16 = nil
        local v_u_17 = nil
        v_u_2:get_base_fn(v12, "setup_stage")
        v12.setup_stage = function(p18, p19) --[[ Name: setup_stage ]] --[[ Line: 45 ]]
            --[[ Upvalues: (ref 1): v_u_13, (ref 2): v_u_9, (ref 3): v_u_5, (ref 4): v_u_6, (ref 5): v_u_4, (ref 6): v_u_16, (ref 7): v_u_17, (ref 8): v_u_10, (ref 9): v_u_11 ]]
            v_u_13.Parent = v_u_9:get_local_elements_folder()
            local v20 = v_u_9:get_game_sky()
            v20.SkyboxBk = "rbxassetid://9432526822"
            v20.SkyboxDn = "rbxassetid://9432536821"
            v20.SkyboxFt = "rbxassetid://9432526822"
            v20.SkyboxLf = "rbxassetid://9432526822"
            v20.SkyboxRt = "rbxassetid://9432526822"
            v20.SkyboxUp = "rbxassetid://9432536976"
            if p19._player_settings_manager:get_key(v_u_5.Key.BrightnessSettings) == v_u_6.Normal then
                local v21 = v_u_9:get_game_lighting()
                v21.Brightness = 1
                v21.Ambient = v_u_4:new(0, 0, 0):to_color3()
                v21.ColorShift_Bottom = v_u_4:new(120, 33, 195):to_color3()
                v21.ColorShift_Top = v_u_4:new(38, 0, 165):to_color3()
            end;
            v_u_16 = v_u_13.ShrineSet
            p18:on_switch_focus_slot(p19)
            v_u_17 = v_u_10:new(game.ReplicatedStorage.ElementProtos.CharacterShineEffectProto, v_u_11.CHARACTER_POSITION_OFFSET)
        end;
        v_u_2:get_base_fn(v12, "on_switch_focus_slot")
        v12.on_switch_focus_slot = function(_, p22) --[[ Name: on_switch_focus_slot ]] --[[ Line: 74 ]]
            --[[ Upvalues: (ref 1): v_u_16, (ref 2): v_u_3 ]]
            v_u_16:SetPrimaryPartCFrame(CFrame.new(v_u_3:get_world_center_position(), v_u_3:slot_to_world_position(p22:get_local_game_slot())))
        end;
        v_u_2:get_base_fn(v12, "teardown_stage")
        v12.teardown_stage = function(_, p23) --[[ Name: teardown_stage ]] --[[ Line: 82 ]]
            --[[ Upvalues: (ref 1): v_u_17, (ref 2): v_u_13 ]]
            v_u_17:teardown(p23)
            v_u_13:Destroy()
        end;
        v_u_2:get_base_fn(v12, "create_shine_for_slot_at_cframe")
        v12.create_shine_for_slot_at_cframe = function(_, p24, p25, p26) --[[ Name: create_shine_for_slot_at_cframe ]] --[[ Line: 89 ]]
            --[[ Upvalues: (ref 1): v_u_17 ]]
            v_u_17:create_shine_for_slot_at_cframe(p24, p25, p26)
        end;
        v_u_2:get_base_fn(v12, "game_update")
        v12.game_update = function(_, p27, p28) --[[ Name: game_update ]] --[[ Line: 94 ]]
            --[[ Upvalues: (ref 1): v_u_17 ]]
            v_u_17:update(p27, p28)
        end;
        v_u_2:get_base_fn(v12, "should_do_game_start_zoom_in_effect")
        v12.should_do_game_start_zoom_in_effect = function(_) --[[ Name: should_do_game_start_zoom_in_effect ]] --[[ Line: 99 ]]
            return true, 49.275000000000006, 18.900000000000002, 0.75;
        end;
        return v12;
    end
};
