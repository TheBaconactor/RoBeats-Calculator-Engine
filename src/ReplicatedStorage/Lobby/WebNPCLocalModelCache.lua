-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:35 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Avatar.CreateCharacter)
local v_u_2 = require(game.ReplicatedStorage.Avatar.SanitizeCharacter)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_4 = require(game.ReplicatedStorage.Local.DebugOut)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_6 = require(game.ReplicatedStorage.Shared.NoCollideGroup)
local v_u_7 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_8 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local l_Players_0 = game.Players
return {
    ["new"] = function(_) --[[ Name: new ]] --[[ Line: 14 ]]
        --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_8, (copy 3): v_u_5, (copy 4): l_Players_0, (copy 5): v_u_4, (copy 6): v_u_7, (copy 7): v_u_1, (copy 8): v_u_2, (copy 9): v_u_6 ]]
        local v9 = {}
        local v_u_10 = v_u_3:new()
        local v_u_11 = v_u_3:new()
        local v_u_12 = nil
        local v_u_13 = nil
        pcall(function() --[[ Line: 21 ]]
            --[[ Upvalues: (ref 1): v_u_12, (ref 2): v_u_8, (ref 3): v_u_13, (ref 4): v_u_5 ]]
            v_u_12 = v_u_8:get_default_character_clone()
            v_u_13 = v_u_5:first_child_of_type(v_u_12, "Humanoid"):GetAppliedDescription()
        end)
        v9.mark_for_delete_all_cached_models = function(_) --[[ Name: mark_for_delete_all_cached_models ]] --[[ Line: 26 ]]
            --[[ Upvalues: (copy 1): v_u_10, (copy 2): v_u_11 ]]
            for v14, _ in v_u_10:key_itr() do
                v_u_11:add(v14, true)
            end;
        end;
        v9.unmark_for_delete_playerid = function(_, p15) --[[ Name: unmark_for_delete_playerid ]] --[[ Line: 32 ]]
            --[[ Upvalues: (copy 1): v_u_11 ]]
            v_u_11:remove(p15)
        end;
        v9.clear_all_marked_for_delete_models = function(_) --[[ Name: clear_all_marked_for_delete_models ]] --[[ Line: 36 ]]
            --[[ Upvalues: (copy 1): v_u_11, (copy 2): v_u_10 ]]
            for v16, _ in v_u_11:key_itr() do
                v_u_10:get(v16):Destroy()
                v_u_10:remove(v16)
            end;
            v_u_11:clear()
        end;
        local function f_create_character_for_playerid_async(p_u_17) --[[ Name: create_character_for_playerid_async ]] --[[ Line: 44 ]]
            --[[ Upvalues: (ref 1): l_Players_0, (ref 2): v_u_13, (ref 3): v_u_4, (ref 4): v_u_5, (ref 5): v_u_8 ]]
            local v_u_18 = nil
            local v20, _ = pcall(function() --[[ Line: 46 ]]
                --[[ Upvalues: (ref 1): l_Players_0, (copy 2): p_u_17, (ref 3): v_u_13, (ref 4): v_u_18 ]]
                local v19 = l_Players_0:GetHumanoidDescriptionFromUserId(p_u_17)
                if v_u_13 then
                    v19.BodyTypeScale = v_u_13.BodyTypeScale
                    v19.DepthScale = v_u_13.DepthScale
                    v19.ProportionScale = v_u_13.ProportionScale
                    v19.HeadScale = v_u_13.HeadScale
                    v19.HeightScale = v_u_13.HeightScale
                end;
                v_u_18 = l_Players_0:CreateHumanoidModelFromDescription(v19, Enum.HumanoidRigType.R15)
            end)
            if v20 ~= true then
                v_u_4:warnf("Could not create character for playerid(%s)", (tostring(p_u_17)))
            end;
            local v21
            if v_u_18 == nil or (typeof(v_u_18) ~= "Instance" or (v_u_18.PrimaryPart == nil or v_u_5:first_child_of_type(v_u_18, "Humanoid") == nil)) then
                v_u_18 = v_u_8:get_default_character_clone()
                v21 = v_u_18
            else
                v21 = v_u_18
            end;
            return v21;
        end;
        v9.create_cached_character_model_for_playerid = function(_, p22, p23) --[[ Name: create_cached_character_model_for_playerid ]] --[[ Line: 72 ]]
            --[[ Upvalues: (copy 1): v_u_10, (ref 2): v_u_7, (copy 3): f_create_character_for_playerid_async, (ref 4): v_u_1, (ref 5): v_u_2, (ref 6): v_u_6 ]]
            if v_u_10:contains(p22) ~= true then
                local v24
                if v_u_7.WebNPCCacheUsePlayersCreateCharacter == true then
                    v24 = f_create_character_for_playerid_async(p22)
                else
                    v24 = v_u_1(p22)
                end;
                v_u_2:sanitize_model(v24)
                v_u_6:apply_group_id(v24, p23)
                v_u_10:add(p22, v24)
            end;
            return v_u_10:get(p22):Clone();
        end;
        v9.get_cached_count = function(_) --[[ Name: get_cached_count ]] --[[ Line: 88 ]]
            --[[ Upvalues: (copy 1): v_u_10, (copy 2): v_u_11 ]]
            return v_u_10:count() + v_u_11:count();
        end;
        return v9;
    end
};
