-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:18 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Server.DebugOut)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
require(game.ReplicatedStorage.Shared.DebugConfig)
require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_5 = require(game.ReplicatedStorage.PlayerInfo.Collection.CollectionInfo)
local v_u_6 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_7 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_8 = require(game.ReplicatedStorage.Server.ServerAPIManager)
local v_u_9 = require(game.ReplicatedStorage.Shared.WaitForFinish)
local v_u_10 = require(game.ReplicatedStorage.Avatar.PlayerBlobAvatar)
local v_u_11 = require(game.ReplicatedStorage.Avatar.SPAvatarEquipmentDatabase)
local v_u_12 = require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
local s_HttpService_0 = game:GetService("HttpService")
return {
    ["new"] = function(_, p_u_13) --[[ Name: new ]] --[[ Line: 21 ]]
        --[[ Upvalues: (copy 1): v_u_3, (copy 2): s_HttpService_0, (copy 3): v_u_7, (copy 4): v_u_8, (copy 5): v_u_1, (copy 6): v_u_4, (copy 7): v_u_6, (copy 8): v_u_5, (copy 9): v_u_2, (copy 10): v_u_12, (copy 11): v_u_9, (copy 12): v_u_10, (copy 13): v_u_11 ]]
        local v14 = {}
        local v_u_15 = v_u_3:new()
        local v_u_16 = v_u_3:new()
        local v_u_17 = v_u_3:new()
        v14.start = function(p_u_18) --[[ Name: start ]] --[[ Line: 29 ]]
            --[[ Upvalues: (copy 1): v_u_16, (copy 2): v_u_17, (ref 3): s_HttpService_0, (copy 4): p_u_13, (ref 5): v_u_7, (copy 6): v_u_15, (ref 7): v_u_8, (ref 8): v_u_1, (ref 9): v_u_4, (ref 10): v_u_6, (ref 11): v_u_5, (ref 12): v_u_2, (ref 13): v_u_12, (ref 14): v_u_9, (ref 15): v_u_10, (ref 16): v_u_11 ]]
            local function f_write_updated_collection_info_and_sync_playerblob(p_u_19, p20, p_u_21, p_u_22, p_u_23, p_u_24) --[[ Name: write_updated_collection_info_and_sync_playerblob ]] --[[ Line: 31 ]]
                --[[ Upvalues: (ref 1): v_u_16, (ref 2): v_u_17, (ref 3): s_HttpService_0, (ref 4): p_u_13, (ref 5): v_u_7, (ref 6): v_u_15, (ref 7): v_u_8, (ref 8): v_u_1 ]]
                p20.CollectionInfoJson = p_u_19:to_json()
                v_u_16:remove(p_u_23.UserId)
                v_u_17:remove(p_u_23.UserId)
                local v_u_25 = {}
                local v_u_26 = ""
                pcall(function() --[[ Line: 40 ]]
                    --[[ Upvalues: (ref 1): v_u_25, (copy 2): p_u_21, (copy 3): p_u_22, (copy 4): p_u_19, (ref 5): v_u_26, (ref 6): s_HttpService_0 ]]
                    v_u_25 = {
                        ["CollectionType"] = p_u_21,
                        ["RegisteredIDs"] = p_u_22:get_table(),
                        ["UpdatedCollectionInfo"] = p_u_19:to_table(),
                        ["Time"] = os.time()
                    }
                    v_u_26 = s_HttpService_0:JSONEncode(v_u_25)
                end)
                p_u_13._player_blob_manager:enqueue_blob_sync_request(p_u_23.UserId, v_u_7.PlayerBlobRequestType.Write, function() --[[ Line: 53 ]]
                    --[[ Upvalues: (copy 1): p_u_24, (ref 2): v_u_15, (copy 3): p_u_23, (copy 4): p_u_19, (ref 5): p_u_13, (ref 6): v_u_25, (ref 7): v_u_8, (copy 8): p_u_22, (ref 9): v_u_26, (ref 10): v_u_1 ]]
                    p_u_24()
                    v_u_15:add(p_u_23.UserId, p_u_19)
                    p_u_13._datastore_api:log_collection_register_for_playerid(p_u_23.UserId, v_u_25)
                    p_u_13._api:api_report_evt(v_u_8.ReportEvt_CollectionRegister, p_u_23.UserId, p_u_22:count(), v_u_26)
                    v_u_1:puts("EVT_Collection_RegisterAllOfCollectionType_Client player(%d) registered_data_str(%s)", p_u_23.UserId, v_u_26)
                end)
            end;
            p_u_13._evt:wait_on_event(v_u_4.EVT_Collection_RegisterCollectionTypeAndID_Client, function(p_u_27, p_u_28, p_u_29) --[[ Line: 64 ]]
                --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_5, (ref 3): p_u_13, (ref 4): v_u_4, (copy 5): p_u_18, (ref 6): v_u_2, (copy 7): f_write_updated_collection_info_and_sync_playerblob ]]
                v_u_6:is_enum_member(p_u_28, v_u_5.Type)
                v_u_6:is_int(p_u_29)
                local v_u_30 = v_u_5:get_entry_for_collection_type_and_collection_id(p_u_28, p_u_29)
                v_u_6:is_non_nil(v_u_30)
                local function f_response(p31) --[[ Name: response ]] --[[ Line: 71 ]]
                    --[[ Upvalues: (ref 1): p_u_13, (ref 2): v_u_4, (copy 3): p_u_27 ]]
                    p_u_13._evt:fire_event_to_client(v_u_4.EVT_Collection_RegisterCollectionTypeAndID_Server, p_u_27, p31)
                end;
                p_u_13._player_blob_manager:get_verified_cached_blob(p_u_27.UserId, function(p32) --[[ Line: 75 ]]
                    --[[ Upvalues: (ref 1): p_u_18, (copy 2): p_u_27, (copy 3): p_u_28, (copy 4): p_u_29, (copy 5): f_response, (copy 6): v_u_30, (ref 7): v_u_2, (ref 8): f_write_updated_collection_info_and_sync_playerblob, (ref 9): p_u_13, (ref 10): v_u_4 ]]
                    local v33 = p_u_18:get_collection_info_for_player_id_playerblob(p_u_27.UserId, p32)
                    if v33:get_collection_type_and_id_owned(p_u_28, p_u_29) == true then
                        return f_response(0);
                    end;
                    if v_u_30:does_playerblob_own_entry(p32) ~= true then
                        return f_response(0);
                    end;
                    if v_u_30:try_register_entry_to_playerblob(p32) then
                        v33:set_collection_type_and_id_owned(p_u_28, p_u_29, true)
                    end;
                    local v_u_34 = v_u_2:new()
                    v_u_34:push_back(p_u_29)
                    f_write_updated_collection_info_and_sync_playerblob(v33, p32, p_u_28, v_u_34, p_u_27, function() --[[ Line: 87 ]]
                        --[[ Upvalues: (copy 1): v_u_34, (ref 2): p_u_13, (ref 3): v_u_4, (ref 4): p_u_27 ]]
                        p_u_13._evt:fire_event_to_client(v_u_4.EVT_Collection_RegisterCollectionTypeAndID_Server, p_u_27, (v_u_34:count()))
                    end)
                end)
            end)
            p_u_13._evt:wait_on_event(v_u_4.EVT_Collection_RegisterAllOfCollectionType_Client, function(p_u_35, p_u_36) --[[ Line: 93 ]]
                --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_5, (ref 3): p_u_13, (ref 4): v_u_4, (copy 5): p_u_18, (ref 6): v_u_2, (copy 7): f_write_updated_collection_info_and_sync_playerblob ]]
                v_u_6:is_enum_member(p_u_36, v_u_5.Type)
                local function _(p37) --[[ Name: response ]] --[[ Line: 96 ]]
                    --[[ Upvalues: (ref 1): p_u_13, (ref 2): v_u_4, (copy 3): p_u_35 ]]
                    p_u_13._evt:fire_event_to_client(v_u_4.EVT_Collection_RegisterAllOfCollectionType_Server, p_u_35, p37)
                end;
                p_u_13._player_blob_manager:get_verified_cached_blob(p_u_35.UserId, function(p38) --[[ Line: 100 ]]
                    --[[ Upvalues: (ref 1): p_u_18, (copy 2): p_u_35, (ref 3): v_u_5, (copy 4): p_u_36, (ref 5): v_u_2, (ref 6): f_write_updated_collection_info_and_sync_playerblob, (ref 7): p_u_13, (ref 8): v_u_4 ]]
                    local v39 = p_u_18:get_collection_info_for_player_id_playerblob(p_u_35.UserId, p38)
                    local v40 = v_u_5:get_playerblob_collection_type_collection_info_unregistered_owned_entries_list(p38, p_u_36, v39)
                    if v40:count() > 0 then
                        local v_u_41 = v_u_2:new()
                        for _, v42 in v40:key_itr() do
                            if v42:try_register_entry_to_playerblob(p38) then
                                v39:set_collection_type_and_id_owned(v42:get_collection_type(), v42:get_collection_id(), true)
                                v_u_41:push_back(v42:get_collection_id())
                            end;
                        end;
                        f_write_updated_collection_info_and_sync_playerblob(v39, p38, p_u_36, v_u_41, p_u_35, function() --[[ Line: 113 ]]
                            --[[ Upvalues: (copy 1): v_u_41, (ref 2): p_u_13, (ref 3): v_u_4, (ref 4): p_u_35 ]]
                            p_u_13._evt:fire_event_to_client(v_u_4.EVT_Collection_RegisterAllOfCollectionType_Server, p_u_35, (v_u_41:count()))
                        end)
                    else
                        p_u_13._evt:fire_event_to_client(v_u_4.EVT_Collection_RegisterAllOfCollectionType_Server, p_u_35, 0)
                    end;
                end)
            end)
            p_u_13._evt:wait_on_event(v_u_4.EVT_Collection_CheckPointsClient, function(p_u_43) --[[ Line: 122 ]]
                --[[ Upvalues: (ref 1): p_u_13, (ref 2): v_u_4, (ref 3): v_u_16, (ref 4): v_u_5, (copy 5): p_u_18, (ref 6): v_u_2, (ref 7): v_u_12 ]]
                local function f_response(p44, p45) --[[ Name: response ]] --[[ Line: 123 ]]
                    --[[ Upvalues: (ref 1): p_u_13, (ref 2): v_u_4, (copy 3): p_u_43 ]]
                    p_u_13._evt:fire_event_to_client(v_u_4.EVT_Collection_CheckPointsServer, p_u_43, p44:to_table(), p45 == nil and {} or p45)
                end;
                local l_UserId_0 = p_u_43.UserId
                if v_u_16:contains(l_UserId_0) then
                    return f_response(v_u_16:get(l_UserId_0));
                end;
                p_u_13._player_blob_manager:get_verified_cached_blob(p_u_43.UserId, function(p_u_46) --[[ Line: 132 ]]
                    --[[ Upvalues: (ref 1): v_u_5, (copy 2): l_UserId_0, (copy 3): p_u_43, (ref 4): p_u_18, (ref 5): v_u_2, (ref 6): v_u_12, (ref 7): p_u_13, (ref 8): v_u_16, (ref 9): v_u_4 ]]
                    local v_u_47 = v_u_5.CollectionLeaderboardEntry:new(l_UserId_0, p_u_43.Name)
                    local v48 = p_u_18:get_collection_info_for_player_id_playerblob(l_UserId_0, p_u_46)
                    for v49, _ in v_u_5:get_all_collection_types_set():key_itr() do
                        local v50 = 0
                        for _, v51 in v48:get_collection_type_owned_entry_list(v49):key_itr() do
                            v50 = v50 + v51:get_collection_point_amount()
                        end;
                        v_u_47:set_type_point_amount(v49, v50)
                        v_u_47:set_overall_point_amount(v_u_47:get_overall_point_amount() + v50)
                    end;
                    (function(p_u_52) --[[ Name: check_rewards_and_update ]] --[[ Line: 145 ]]
                        --[[ Upvalues: (ref 1): v_u_2, (copy 2): v_u_47, (ref 3): v_u_5, (ref 4): v_u_12, (copy 5): p_u_46, (ref 6): p_u_13, (ref 7): p_u_43 ]]
                        local v_u_53 = v_u_2:new()
                        local v54 = v_u_47:get_overall_point_amount()
                        local v55, v56 = v_u_5:get_title_id_to_collection_point_amount()
                        for _, v57 in v55:key_itr() do
                            if v56:get(v57) <= v54 then
                                local v58 = v_u_12.RewardInfo:new(v_u_12.RewardType.Titles, 1, v57)
                                if v58:can_playerblob_add(p_u_46) then
                                    v_u_53:push_back(v58)
                                end;
                            end;
                        end;
                        if v_u_53:count() == 0 then
                            p_u_52()
                        else
                            v_u_12:server_sync_reward_params(p_u_13, p_u_43, v_u_12:claim_reward_info_list_to_playerblob(p_u_13, p_u_46, v_u_53), function(_) --[[ Line: 164 ]]
                                --[[ Upvalues: (copy 1): p_u_52, (ref 2): v_u_12, (copy 3): v_u_53 ]]
                                p_u_52(v_u_12.RewardInfo:list_to_table(v_u_53))
                            end)
                        end;
                    end)(function(p_u_59) --[[ Line: 170 ]]
                        --[[ Upvalues: (ref 1): v_u_16, (ref 2): l_UserId_0, (copy 3): v_u_47, (ref 4): p_u_13, (ref 5): v_u_4, (ref 6): p_u_43 ]]
                        v_u_16:add(l_UserId_0, v_u_47)
                        p_u_13._datastore_api:write_collection_leaderboard_entry(v_u_47)
                        p_u_13._api:api_collection_leaderboard_register(v_u_47, function() --[[ Line: 173 ]]
                            --[[ Upvalues: (ref 1): v_u_47, (copy 2): p_u_59, (ref 3): p_u_13, (ref 4): v_u_4, (ref 5): p_u_43 ]]
                            local v60 = p_u_59
                            p_u_13._evt:fire_event_to_client(v_u_4.EVT_Collection_CheckPointsServer, p_u_43, v_u_47:to_table(), v60 == nil and {} or v60)
                        end)
                    end)
                end)
            end)
            p_u_13._evt:wait_on_event(v_u_4.EVT_Collection_GetLeaderboardClient, function(p_u_61) --[[ Line: 181 ]]
                --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_5, (ref 3): v_u_9, (ref 4): p_u_13, (ref 5): v_u_4, (ref 6): v_u_17 ]]
                local v_u_62 = v_u_2:new()
                local v_u_63 = v_u_5.CollectionLeaderboardRankData:new(-1)
                local v_u_64 = v_u_9:new(2, function() --[[ Line: 185 ]]
                    --[[ Upvalues: (ref 1): p_u_13, (ref 2): v_u_4, (copy 3): p_u_61, (ref 4): v_u_5, (ref 5): v_u_62, (ref 6): v_u_63 ]]
                    p_u_13._evt:fire_event_to_client(v_u_4.EVT_Collection_GetLeaderboardServer, p_u_61, v_u_5.CollectionLeaderboardEntry:list_to_table(v_u_62), v_u_63:to_table())
                end)
                p_u_13._datastore_api:get_collection_leaderboard_entries_list(function(p65) --[[ Line: 194 ]]
                    --[[ Upvalues: (ref 1): v_u_62, (copy 2): v_u_64 ]]
                    v_u_62 = p65
                    v_u_64:finish()
                end)
                if v_u_17:contains(p_u_61.UserId) then
                    v_u_63 = v_u_17:get(p_u_61.UserId)
                    v_u_64:finish()
                else
                    p_u_13._api:api_collection_leaderboard_check_ranks(p_u_61.UserId, function(p66, p67) --[[ Line: 202 ]]
                        --[[ Upvalues: (ref 1): v_u_63, (ref 2): v_u_5, (ref 3): v_u_17, (copy 4): p_u_61, (copy 5): v_u_64 ]]
                        if p66 then
                            v_u_63 = v_u_5.CollectionLeaderboardRankData:from_table(p67)
                            v_u_17:add(p_u_61.UserId, v_u_63)
                        end;
                        v_u_64:finish()
                    end)
                end;
            end)
            p_u_13._evt:wait_on_event(v_u_4.EVT_Collection_OverrideGearAppearanceClient, function(p_u_68, p_u_69, p_u_70) --[[ Line: 212 ]]
                --[[ Upvalues: (ref 1): p_u_13, (ref 2): v_u_4, (ref 3): v_u_10, (ref 4): v_u_11, (ref 5): v_u_5, (copy 6): p_u_18, (ref 7): v_u_7 ]]
                local function f_response(p71, p72) --[[ Name: response ]] --[[ Line: 213 ]]
                    --[[ Upvalues: (ref 1): p_u_13, (ref 2): v_u_4, (copy 3): p_u_68 ]]
                    p_u_13._evt:fire_event_to_client(v_u_4.EVT_Collection_OverrideGearAppearanceServer, p_u_68, p71, p72)
                end;
                p_u_13._player_blob_manager:get_verified_cached_blob(p_u_68.UserId, function(p_u_73) --[[ Line: 217 ]]
                    --[[ Upvalues: (copy 1): f_response, (ref 2): v_u_10, (copy 3): p_u_69, (ref 4): v_u_11, (ref 5): v_u_5, (copy 6): p_u_70, (ref 7): p_u_18, (copy 8): p_u_68, (ref 9): p_u_13, (ref 10): v_u_7, (ref 11): v_u_4 ]]
                    if p_u_73 == nil then
                        return f_response(false, "Playerblob not found");
                    end;
                    local v74, v75 = v_u_10:playerblob_ownedid_to_equipmentid(p_u_73, p_u_69)
                    if v75 == nil then
                        return f_response(false, "Owned gear not found");
                    end;
                    local v_u_76 = v_u_11:singleton():get_equipment_for_id(v74)
                    local v77 = v_u_5:get_entry_for_collection_type_and_collection_id(v_u_5.Type.Gear, p_u_70)
                    if v77 == nil then
                        return f_response(false, "Collection entry not found");
                    end;
                    if p_u_18:get_collection_info_for_player_id_playerblob(p_u_68.UserId, p_u_73):get_collection_type_and_id_owned(v77:get_collection_type(), v77:get_collection_id()) ~= true then
                        return f_response(false, "Collection entry not owned");
                    end;
                    local v78 = v_u_11:singleton():get_equipment_for_id(v77:get_database_id())
                    if v_u_76 == nil or v78 == nil then
                        return f_response(false, "Equipment not found");
                    end;
                    if v_u_76:get_avatar_slot() ~= v78:get_avatar_slot() then
                        return f_response(false, "Slot not matching");
                    end;
                    v75.OAID = v77:get_database_id()
                    p_u_13._player_blob_manager:enqueue_blob_sync_request(p_u_68.UserId, v_u_7.PlayerBlobRequestType.Write, function() --[[ Line: 243 ]]
                        --[[ Upvalues: (ref 1): p_u_13, (ref 2): p_u_68, (copy 3): p_u_73, (copy 4): v_u_76, (ref 5): v_u_4 ]]
                        p_u_13._lobby_manager:update_player_character_to_equipped_data(p_u_68, p_u_73)
                        p_u_13._evt:fire_event_to_client(v_u_4.EVT_Collection_OverrideGearAppearanceServer, p_u_68, true, (string.format("Changed the appearance of your \'%s\'!", v_u_76:get_name())))
                    end)
                end)
            end)
        end;
        v14.get_collection_info_for_player_id_playerblob = function(_, p79, p80) --[[ Name: get_collection_info_for_player_id_playerblob ]] --[[ Line: 255 ]]
            --[[ Upvalues: (copy 1): v_u_15, (ref 2): v_u_5 ]]
            if v_u_15:contains(p79) then
                return v_u_15:get(p79);
            end;
            local v81 = v_u_5:get_collection_info_from_playerblob(p80)
            v_u_15:add(p79, v81)
            return v81;
        end;
        v14.player_disconnecting = function(_, p82) --[[ Name: player_disconnecting ]] --[[ Line: 265 ]]
            --[[ Upvalues: (copy 1): v_u_15, (copy 2): v_u_16, (copy 3): v_u_17 ]]
            v_u_15:remove(p82)
            v_u_16:remove(p82)
            v_u_17:remove(p82)
        end;
        return v14;
    end
};
