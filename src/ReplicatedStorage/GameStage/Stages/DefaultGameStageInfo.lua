-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:22:05 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.GameStage.StageInfoBase)
local v_u_2 = require(game.ReplicatedStorage.Shared.Override)
require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_3 = require(game.ReplicatedStorage.Shared.PlayerSettings)
local v_u_4 = require(game.ReplicatedStorage.Shared.BrightnessSettings)
local v_u_5 = require(game.ReplicatedStorage.Shared.ModelLoadDB)
local v_u_6 = require(game.ReplicatedStorage.Shared.ModelLoadDBAsset)
local v_u_7 = nil
local v_u_8 = nil
local v_u_9 = nil
local v_u_10 = nil
require(game.ReplicatedStorage.Shared.Dependency):require_client(function() --[[ Line: 16 ]]
    --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_8, (ref 3): v_u_9, (ref 4): v_u_10 ]]
    v_u_7 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
    v_u_8 = require(game.ReplicatedStorage.Local.CrowdManager)
    v_u_9 = require(game.ReplicatedStorage.GameStage.Util.GameStageDefaultCharacterShineBehaviour)
    v_u_10 = require(game.ReplicatedStorage.Effects.CharacterShineEffect)
end)
return {
    ["new"] = function(_) --[[ Name: new ]] --[[ Line: 25 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_2, (copy 3): v_u_5, (copy 4): v_u_6, (copy 5): v_u_3, (copy 6): v_u_4, (ref 7): v_u_7, (ref 8): v_u_8, (ref 9): v_u_9, (ref 10): v_u_10 ]]
        local v11 = v_u_1:new()
        v_u_2:get_base_fn(v11, "get_name")
        v11.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 29 ]]
            return "Classic RoBeats Arena";
        end;
        v_u_2:get_base_fn(v11, "get_icon")
        v11.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 31 ]]
            return "rbxassetid://9354237358";
        end;
        local v_u_12 = nil
        v11.load_stage_immediate = function(_) --[[ Name: load_stage_immediate ]] --[[ Line: 35 ]]
            --[[ Upvalues: (ref 1): v_u_12, (ref 2): v_u_5, (ref 3): v_u_6 ]]
            v_u_12 = v_u_5:singleton():get_category_default(v_u_6.Category.GameStage)
        end;
        v11.load_stage = function(p13, p14) --[[ Name: load_stage ]] --[[ Line: 39 ]]
            p13:load_stage_immediate()
            p14()
        end;
        local v_u_15 = nil
        local v_u_16 = nil
        local v_u_17 = nil
        v_u_2:get_base_fn(v11, "setup_stage")
        v11.setup_stage = function(_, p18) --[[ Name: setup_stage ]] --[[ Line: 49 ]]
            --[[ Upvalues: (ref 1): v_u_15, (ref 2): v_u_12, (ref 3): v_u_3, (ref 4): v_u_4, (ref 5): v_u_7, (ref 6): v_u_16, (ref 7): v_u_8, (ref 8): v_u_17, (ref 9): v_u_9, (ref 10): v_u_10 ]]
            v_u_15 = v_u_12.Crowd
            local l_SurfaceLight_0 = v_u_12.Background.Ceiling.Lighting.SurfaceLight
            local l_Bumper_0 = v_u_12.Background.Stage.Bumper
            if p18._player_settings_manager:get_key(v_u_3.Key.BrightnessSettings) == v_u_4.Dark then
                l_SurfaceLight_0.Enabled = false
                l_Bumper_0.Transparency = 0.75
            else
                l_SurfaceLight_0.Enabled = true
                l_Bumper_0.Transparency = 0
            end;
            v_u_12.Parent = v_u_7:get_local_elements_folder()
            v_u_16 = v_u_8:new(v_u_15)
            v_u_16:load_crowd(p18)
            v_u_17 = v_u_9:new(game.ReplicatedStorage.ElementProtos.CharacterShineEffectProto, v_u_10.CHARACTER_POSITION_OFFSET)
        end;
        v_u_2:get_base_fn(v11, "teardown_stage")
        v11.teardown_stage = function(_, p19) --[[ Name: teardown_stage ]] --[[ Line: 72 ]]
            --[[ Upvalues: (ref 1): v_u_16, (ref 2): v_u_17, (ref 3): v_u_12 ]]
            v_u_16:teardown(p19)
            v_u_17:teardown(p19)
            v_u_12:Destroy()
        end;
        v_u_2:get_base_fn(v11, "create_shine_for_slot_at_cframe")
        v11.create_shine_for_slot_at_cframe = function(_, p20, p21, p22) --[[ Name: create_shine_for_slot_at_cframe ]] --[[ Line: 80 ]]
            --[[ Upvalues: (ref 1): v_u_17 ]]
            v_u_17:create_shine_for_slot_at_cframe(p20, p21, p22)
        end;
        v_u_2:get_base_fn(v11, "game_update")
        v11.game_update = function(_, p23, p24) --[[ Name: game_update ]] --[[ Line: 85 ]]
            --[[ Upvalues: (ref 1): v_u_16, (ref 2): v_u_17 ]]
            if v_u_16:has_loaded_friends() == false and p24:es_gamelocal_get_audiomanager():is_ready_to_play() == true then
                v_u_16:load_friends_into_crowd()
            end;
            v_u_16:update(p23, p24)
            v_u_17:update(p23, p24)
        end;
        return v11;
    end
};
