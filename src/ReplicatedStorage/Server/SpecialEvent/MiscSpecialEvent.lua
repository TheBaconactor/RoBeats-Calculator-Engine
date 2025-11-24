-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:20 PM
-- Cached decompilation

require(game.ReplicatedStorage.Shared.AssertType)
local v_u_1 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
require(game.ReplicatedStorage.Shared.Override)
require(game.ReplicatedStorage.Avatar.PlayerBlobDance)
local v_u_2 = require(game.ReplicatedStorage.Crafting.PlayerBlobCrafting)
local v_u_3 = require(game.ReplicatedStorage.Crafting.CraftDatabase)
local v_u_4 = require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.AudioData.SongDatabase)
require(game.ReplicatedStorage.Server.DebugOut)
require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_6 = require(game.ReplicatedStorage.PlayerInfo.Collection.CollectionInfo)
local _ = game:GetService("BadgeService")
local _ = game:GetService("TeleportService")
local v_u_7 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_8 = require(game.ReplicatedStorage.PlayerInfo.SpecialEventInfoData.MiscEventInfo)
local v9 = {}
local v10 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_11 = nil
v10:require_server(function() --[[ Line: 23 ]]
    --[[ Upvalues: (ref 1): v_u_11 ]]
    v_u_11 = require(game.ReplicatedStorage.Server.ServerSpecialEventManager)
end)
v9.new = function(_, p_u_12) --[[ Name: new ]] --[[ Line: 27 ]]
    --[[ Upvalues: (ref 1): v_u_11, (copy 2): v_u_7, (copy 3): v_u_1, (copy 4): v_u_8, (copy 5): v_u_5, (copy 6): v_u_4, (copy 7): v_u_3, (copy 8): v_u_2, (copy 9): v_u_6 ]]
    local v13 = v_u_11.EventBase:new()
    local v_u_14 = v_u_7:new()
    local function _() --[[ Name: cons ]] --[[ Line: 32 ]]
        --[[ Upvalues: (copy 1): p_u_12, (ref 2): v_u_1, (copy 3): v_u_14, (ref 4): v_u_8, (ref 5): v_u_5, (ref 6): v_u_4, (ref 7): v_u_3, (ref 8): v_u_2, (ref 9): v_u_6 ]]
        p_u_12._evt:wait_on_event(v_u_1.EVT_SpecialEvent_Misc_ClientRequest1, function(p_u_15) --[[ Line: 33 ]]
            --[[ Upvalues: (ref 1): p_u_12, (ref 2): v_u_1, (ref 3): v_u_14, (ref 4): v_u_8, (ref 5): v_u_5, (ref 6): v_u_4, (ref 7): v_u_3, (ref 8): v_u_2, (ref 9): v_u_6 ]]
            local function f_response(p16, p17, p18) --[[ Name: response ]] --[[ Line: 34 ]]
                --[[ Upvalues: (ref 1): p_u_12, (ref 2): v_u_1, (copy 3): p_u_15 ]]
                p_u_12._evt:fire_event_to_client(v_u_1.EVT_SpecialEvent_Misc_ServerResponse1, p_u_15, p16, p17, p18 == nil and {} or p18)
            end;
            if v_u_14:contains(p_u_15.UserId) then
                return f_response(false, "Already claimed.");
            end;
            p_u_12._player_blob_manager:get_verified_cached_blob(p_u_15.UserId, function(p19) --[[ Line: 43 ]]
                --[[ Upvalues: (ref 1): v_u_8, (ref 2): p_u_12, (copy 3): f_response, (ref 4): v_u_5, (ref 5): v_u_4, (ref 6): v_u_3, (ref 7): v_u_2, (ref 8): v_u_6, (ref 9): v_u_14, (copy 10): p_u_15, (ref 11): v_u_1 ]]
                if v_u_8:is_event_active(p_u_12._api:get_day_event_list(), p19) ~= true then
                    return f_response(false, "Event not active.");
                end;
                local v20 = v_u_5:new()
                for _, v21 in v_u_8:get_listening_party_reward_list():key_itr() do
                    if v21:get_type() == v_u_4.RewardType.Titles then
                        if v21:can_playerblob_add(p19) then
                            v20:push_back(v21)
                        end;
                    elseif v21:get_type() == v_u_4.RewardType.CraftingMaterials then
                        local v22 = v21:get_id()
                        if v_u_3:singleton():get_material(v22):is_fever_icon() == true and (v_u_2:get_count_of_material(p19, v22) == 0 and v_u_6:get_playerblob_collection_type_database_id_owned(p19, v_u_6.Type.Icons, v_u_3:singleton():get_material(v22):get_fever_icon_id(), p_u_12._collection_manager:get_collection_info_for_player_id_playerblob(p19.UserId, p19)) == false) then
                            v_u_14:add_set(p_u_15.UserId)
                            v20:push_back(v21)
                        end;
                    end;
                end;
                if v20:count() == 0 then
                    return f_response(false, "Already claimed.");
                end;
                v_u_4:server_sync_reward_params(p_u_12, p_u_15, v_u_4:claim_reward_info_list_to_playerblob(p_u_12, p19, v20), function(_, _, p23) --[[ Line: 81 ]]
                    --[[ Upvalues: (ref 1): v_u_4, (ref 2): p_u_12, (ref 3): v_u_1, (ref 4): p_u_15 ]]
                    local v24 = v_u_4.RewardInfo:list_to_table(p23)
                    p_u_12._evt:fire_event_to_client(v_u_1.EVT_SpecialEvent_Misc_ServerResponse1, p_u_15, true, "", v24 == nil and {} or v24)
                end)
            end)
        end)
    end;
    p_u_12._evt:wait_on_event(v_u_1.EVT_SpecialEvent_Misc_ClientRequest1, function(p_u_25) --[[ Line: 33 ]]
        --[[ Upvalues: (copy 1): p_u_12, (ref 2): v_u_1, (copy 3): v_u_14, (ref 4): v_u_8, (ref 5): v_u_5, (ref 6): v_u_4, (ref 7): v_u_3, (ref 8): v_u_2, (ref 9): v_u_6 ]]
        local function f_response(p26, p27, p28) --[[ Name: response ]] --[[ Line: 34 ]]
            --[[ Upvalues: (ref 1): p_u_12, (ref 2): v_u_1, (copy 3): p_u_25 ]]
            p_u_12._evt:fire_event_to_client(v_u_1.EVT_SpecialEvent_Misc_ServerResponse1, p_u_25, p26, p27, p28 == nil and {} or p28)
        end;
        if v_u_14:contains(p_u_25.UserId) then
            return f_response(false, "Already claimed.");
        end;
        p_u_12._player_blob_manager:get_verified_cached_blob(p_u_25.UserId, function(p29) --[[ Line: 43 ]]
            --[[ Upvalues: (ref 1): v_u_8, (ref 2): p_u_12, (copy 3): f_response, (ref 4): v_u_5, (ref 5): v_u_4, (ref 6): v_u_3, (ref 7): v_u_2, (ref 8): v_u_6, (ref 9): v_u_14, (copy 10): p_u_25, (ref 11): v_u_1 ]]
            if v_u_8:is_event_active(p_u_12._api:get_day_event_list(), p29) ~= true then
                return f_response(false, "Event not active.");
            end;
            local v30 = v_u_5:new()
            for _, v31 in v_u_8:get_listening_party_reward_list():key_itr() do
                if v31:get_type() == v_u_4.RewardType.Titles then
                    if v31:can_playerblob_add(p29) then
                        v30:push_back(v31)
                    end;
                elseif v31:get_type() == v_u_4.RewardType.CraftingMaterials then
                    local v32 = v31:get_id()
                    if v_u_3:singleton():get_material(v32):is_fever_icon() == true and (v_u_2:get_count_of_material(p29, v32) == 0 and v_u_6:get_playerblob_collection_type_database_id_owned(p29, v_u_6.Type.Icons, v_u_3:singleton():get_material(v32):get_fever_icon_id(), p_u_12._collection_manager:get_collection_info_for_player_id_playerblob(p29.UserId, p29)) == false) then
                        v_u_14:add_set(p_u_25.UserId)
                        v30:push_back(v31)
                    end;
                end;
            end;
            if v30:count() == 0 then
                return f_response(false, "Already claimed.");
            end;
            v_u_4:server_sync_reward_params(p_u_12, p_u_25, v_u_4:claim_reward_info_list_to_playerblob(p_u_12, p29, v30), function(_, _, p33) --[[ Line: 81 ]]
                --[[ Upvalues: (ref 1): v_u_4, (ref 2): p_u_12, (ref 3): v_u_1, (ref 4): p_u_25 ]]
                local v34 = v_u_4.RewardInfo:list_to_table(p33)
                p_u_12._evt:fire_event_to_client(v_u_1.EVT_SpecialEvent_Misc_ServerResponse1, p_u_25, true, "", v34 == nil and {} or v34)
            end)
        end)
    end)
    return v13;
end;
return v9;
