-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:22:05 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.GameStage.StageInfoBase)
local v_u_2 = require(game.ReplicatedStorage.Shared.Override)
require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_3 = require(game.ReplicatedStorage.Shared.ModelLoadDB)
local v_u_4 = require(game.ReplicatedStorage.Shared.ModelLoadDBAsset)
local v_u_5 = nil
local v_u_6 = nil
local v_u_7 = nil
local v_u_8 = nil
local v_u_9 = nil
require(game.ReplicatedStorage.Shared.Dependency):require_client(function() --[[ Line: 15 ]]
    --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_6, (ref 3): v_u_7, (ref 4): v_u_8, (ref 5): v_u_9 ]]
    v_u_5 = require(game.ReplicatedStorage.Shared.BrightnessSettings)
    v_u_6 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
    v_u_7 = require(game.ReplicatedStorage.Local.CrowdManager)
    v_u_8 = require(game.ReplicatedStorage.GameStage.Util.GameStageDefaultCharacterShineBehaviour)
    v_u_9 = require(game.ReplicatedStorage.Effects.CharacterShineEffect)
end)
return {
    ["new"] = function(_) --[[ Name: new ]] --[[ Line: 25 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_2, (copy 3): v_u_3, (copy 4): v_u_4, (ref 5): v_u_6, (ref 6): v_u_8 ]]
        local v10 = v_u_1:new()
        v_u_2:get_base_fn(v10, "get_name")
        v10.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 29 ]]
            return "Minimalist (Dark Mode)";
        end;
        v_u_2:get_base_fn(v10, "get_icon")
        v10.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 31 ]]
            return "rbxassetid://9354201314";
        end;
        local v_u_11 = nil
        v10.load_stage = function(_, p_u_12) --[[ Name: load_stage ]] --[[ Line: 34 ]]
            --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_4, (ref 3): v_u_11 ]]
            v_u_3:singleton():load_model_category(v_u_4.GameStage.EmptyDarkModeGameStage, v_u_4.Category.GameStage, function(p13) --[[ Line: 35 ]]
                --[[ Upvalues: (ref 1): v_u_11, (copy 2): p_u_12 ]]
                v_u_11 = p13
                p_u_12()
            end)
        end;
        local v_u_14 = nil
        local v_u_15 = nil
        v_u_2:get_base_fn(v10, "setup_stage")
        v10.setup_stage = function(_, _) --[[ Name: setup_stage ]] --[[ Line: 44 ]]
            --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_11, (ref 3): v_u_6, (ref 4): v_u_15, (ref 5): v_u_8 ]]
            v_u_14 = v_u_11.CharacterShineProto
            v_u_14.Parent = nil
            v_u_6:get_game_lighting().ClockTime = 0
            v_u_11.Parent = v_u_6:get_local_elements_folder()
            v_u_15 = v_u_8:new(v_u_14, Vector3.new(0, -3.5, 0))
        end;
        v_u_2:get_base_fn(v10, "create_shine_for_slot_at_cframe")
        v10.create_shine_for_slot_at_cframe = function(_, p16, p17, p18) --[[ Name: create_shine_for_slot_at_cframe ]] --[[ Line: 57 ]]
            --[[ Upvalues: (ref 1): v_u_15 ]]
            v_u_15:create_shine_for_slot_at_cframe(p16, p17, p18)
        end;
        v_u_2:get_base_fn(v10, "game_update")
        v10.game_update = function(_, p19, p20) --[[ Name: game_update ]] --[[ Line: 62 ]]
            --[[ Upvalues: (ref 1): v_u_15 ]]
            v_u_15:update(p19, p20)
        end;
        v_u_2:get_base_fn(v10, "teardown_stage")
        v10.teardown_stage = function(_, p21) --[[ Name: teardown_stage ]] --[[ Line: 67 ]]
            --[[ Upvalues: (ref 1): v_u_15, (ref 2): v_u_11, (ref 3): v_u_14 ]]
            v_u_15:teardown(p21)
            v_u_11:Destroy()
            v_u_14:Destroy()
        end;
        return v10;
    end
};
