-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:22:14 PM
-- Cached decompilation

require(game.ReplicatedStorage.Server.DebugOut)
local v_u_1 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_5 = require(game.ReplicatedStorage.EditorGame.Data.EditorExportData)
local v_u_6 = require(game.ReplicatedStorage.Shared.APICooldown)
local v_u_7 = require(game.ReplicatedStorage.Shared.AssertType)
require(game.ReplicatedStorage.Shared.WaitForFinish)
require(game.ReplicatedStorage.AudioData.SongDatabase)
require(game.ReplicatedStorage.PlayerInfo.ArtistEventInfo)
require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
require(game.ReplicatedStorage.Shared.DebugConfig)
local s_DataStoreService_0 = game:GetService("DataStoreService")
return {
    ["new"] = function(_, p_u_8, p_u_9) --[[ Name: new ]] --[[ Line: 19 ]]
        --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_5, (copy 3): v_u_3, (copy 4): s_DataStoreService_0, (copy 5): v_u_6, (copy 6): v_u_2, (copy 7): v_u_1, (copy 8): v_u_7 ]]
        local v10 = {}
        v10.start = function(p_u_11) --[[ Name: start ]] --[[ Line: 22 ]]
            --[[ Upvalues: (copy 1): p_u_8, (ref 2): v_u_4, (ref 3): v_u_5, (copy 4): p_u_9 ]]
            p_u_8._evt:wait_on_event(v_u_4.EVT_Editor_LikeMap_Client, function(p_u_12, p13) --[[ Line: 23 ]]
                --[[ Upvalues: (ref 1): v_u_5, (ref 2): p_u_8, (ref 3): v_u_4, (ref 4): p_u_9, (copy 5): p_u_11 ]]
                local function f_response(p14, p15, p16, p17) --[[ Name: response ]] --[[ Line: 24 ]]
                    --[[ Upvalues: (ref 1): v_u_5, (ref 2): p_u_8, (ref 3): v_u_4, (copy 4): p_u_12 ]]
                    if p16 == nil then
                        p16 = v_u_5.SavedMapInfo:new()
                    end;
                    if p17 == nil then
                        p17 = false
                    end;
                    p_u_8._evt:fire_event_to_client(v_u_4.EVT_Editor_LikeMap_Server, p_u_12, p14, p15, p16:to_table(), p17)
                end;
                if v_u_5:validate_custom_map_key_components(p13) ~= true then
                    return f_response(false, "Invalid custom map key.");
                end;
                p_u_9:datastore_player_get_key_custom_map_saved_map_info(p_u_12, p13, function(p18, _, p19) --[[ Line: 32 ]]
                    --[[ Upvalues: (copy 1): f_response, (ref 2): p_u_11, (copy 3): p_u_12, (ref 4): v_u_5, (ref 5): p_u_8, (ref 6): v_u_4 ]]
                    if not p18 then
                        return f_response(false, "Could not find custom map data for key.");
                    end;
                    p_u_11:datastore_player_try_like_saved_map_info(p_u_12.UserId, p19, function(p20, p21, p22) --[[ Line: 34 ]]
                        --[[ Upvalues: (ref 1): f_response, (ref 2): v_u_5, (ref 3): p_u_8, (ref 4): v_u_4, (ref 5): p_u_12 ]]
                        if p20 ~= true then
                            return f_response(false, "Already liked map.", p21);
                        end;
                        if p21 == nil then
                            p21 = v_u_5.SavedMapInfo:new()
                        end;
                        if p22 == nil then
                            p22 = false
                        end;
                        p_u_8._evt:fire_event_to_client(v_u_4.EVT_Editor_LikeMap_Server, p_u_12, true, "", p21:to_table(), p22)
                    end)
                end)
            end)
        end;
        local v_u_23 = nil
        v_u_3:ptry(function() --[[ Line: 50 ]]
            --[[ Upvalues: (ref 1): v_u_23, (ref 2): s_DataStoreService_0 ]]
            v_u_23 = s_DataStoreService_0:GetDataStore("EditorGameLikedMapDatastore")
        end)
        local v_u_24 = v_u_6:new():set_cooldown(0.5)
        local v_u_25 = v_u_6:new():set_cooldown(5)
        local v_u_26 = v_u_2:new()
        local function _(p27) --[[ Name: custom_map_data_key_to_liked_playerid_list ]] --[[ Line: 60 ]]
            return string.format("LPID_%s", p27);
        end;
        v10.datastore_player_try_like_saved_map_info = function(p_u_28, p_u_29, p_u_30, p_u_31) --[[ Name: datastore_player_try_like_saved_map_info ]] --[[ Line: 62 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_26, (copy 3): p_u_9, (ref 4): v_u_3, (copy 5): v_u_25, (copy 6): p_u_8, (ref 7): v_u_23, (ref 8): v_u_1 ]]
            if v_u_5:validate_custom_map_key_components(p_u_30:get_custom_map_data_key()) ~= true then
                return p_u_31(false, p_u_30);
            end;
            if v_u_26:contains(p_u_30:get_custom_map_data_key()) and v_u_26:get(p_u_30:get_custom_map_data_key()):contains(p_u_29) then
                return p_u_31(false, p_u_30);
            end;
            local function _() --[[ Name: on_add_new_playerid_like ]] --[[ Line: 72 ]]
                --[[ Upvalues: (ref 1): p_u_9, (copy 2): p_u_30, (copy 3): p_u_29, (copy 4): p_u_31, (ref 5): v_u_3, (copy 6): p_u_28 ]]
                p_u_9:datastore_write_editable_saved_map_info_with_action_no_cooldown(p_u_30, function(p32) --[[ Line: 75 ]]
                    p32:set_like_count(p32:get_like_count() + 1)
                end, function(p_u_33) --[[ Line: 78 ]]
                    --[[ Upvalues: (ref 1): p_u_9, (ref 2): p_u_29, (ref 3): p_u_31, (ref 4): v_u_3, (ref 5): p_u_30, (ref 6): p_u_28 ]]
                    p_u_9:get_playing_manager():on_playerid_added_like_to_saved_map_info(p_u_29, p_u_33, function(p34) --[[ Line: 83 ]]
                        --[[ Upvalues: (ref 1): p_u_31, (copy 2): p_u_33 ]]
                        p_u_31(true, p_u_33, p34)
                    end)
                    v_u_3:spawn(function() --[[ Line: 90 ]]
                        --[[ Upvalues: (ref 1): v_u_3, (ref 2): p_u_9, (ref 3): p_u_30 ]]
                        v_u_3:wait(2.5)
                        p_u_9:datastore_write_creator_data(p_u_30:get_creator_rbxid(), p_u_30:get_creator_name(), function(p35) --[[ Line: 92 ]]
                            p35:set_received_like_count(p35:get_received_like_count() + 1)
                        end)
                    end)
                    v_u_3:spawn(function() --[[ Line: 98 ]]
                        --[[ Upvalues: (ref 1): v_u_3, (ref 2): p_u_28, (ref 3): p_u_29, (copy 4): p_u_33 ]]
                        v_u_3:wait(5)
                        p_u_28:datastore_player_add_liked_map_no_cooldown(p_u_29, p_u_33)
                    end)
                    v_u_3:spawn(function() --[[ Line: 104 ]]
                        --[[ Upvalues: (ref 1): v_u_3, (ref 2): p_u_9, (ref 3): p_u_29, (copy 4): p_u_33 ]]
                        v_u_3:wait(7.5)
                        p_u_9:get_published_map_manager():datastore_player_write_updated_saved_map_info_to_all_categories(p_u_29, p_u_33)
                    end)
                end)
            end;
            v_u_25:queue_key_request(p_u_29, function() --[[ Line: 113 ]]
                --[[ Upvalues: (ref 1): p_u_8, (ref 2): v_u_23, (copy 3): p_u_30, (ref 4): v_u_1, (ref 5): v_u_26, (copy 6): p_u_29, (ref 7): v_u_3, (copy 8): p_u_31, (ref 9): p_u_9, (copy 10): p_u_28 ]]
                p_u_8._datastore_api:do_datastore_update(v_u_23, string.format("LPID_%s", (p_u_30:get_custom_map_data_key())), function(p36) --[[ Line: 117 ]]
                    --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_26, (ref 3): p_u_30, (ref 4): p_u_29, (ref 5): v_u_3, (ref 6): p_u_31, (ref 7): p_u_9, (ref 8): p_u_28 ]]
                    local v37 = v_u_1:new(p36 == nil and {} or p36)
                    v_u_26:add(p_u_30:get_custom_map_data_key(), v37)
                    if v37:contains(p_u_29) == true then
                        v_u_3:spawn(function() --[[ Line: 124 ]]
                            --[[ Upvalues: (ref 1): p_u_31, (ref 2): p_u_30 ]]
                            p_u_31(false, p_u_30)
                        end)
                        return nil;
                    end;
                    v_u_3:spawn(function() --[[ Line: 129 ]]
                        --[[ Upvalues: (ref 1): p_u_9, (ref 2): p_u_30, (ref 3): p_u_29, (ref 4): p_u_31, (ref 5): v_u_3, (ref 6): p_u_28 ]]
                        p_u_9:datastore_write_editable_saved_map_info_with_action_no_cooldown(p_u_30, function(p38) --[[ Line: 75 ]]
                            p38:set_like_count(p38:get_like_count() + 1)
                        end, function(p_u_39) --[[ Line: 78 ]]
                            --[[ Upvalues: (ref 1): p_u_9, (ref 2): p_u_29, (ref 3): p_u_31, (ref 4): v_u_3, (ref 5): p_u_30, (ref 6): p_u_28 ]]
                            p_u_9:get_playing_manager():on_playerid_added_like_to_saved_map_info(p_u_29, p_u_39, function(p40) --[[ Line: 83 ]]
                                --[[ Upvalues: (ref 1): p_u_31, (copy 2): p_u_39 ]]
                                p_u_31(true, p_u_39, p40)
                            end)
                            v_u_3:spawn(function() --[[ Line: 90 ]]
                                --[[ Upvalues: (ref 1): v_u_3, (ref 2): p_u_9, (ref 3): p_u_30 ]]
                                v_u_3:wait(2.5)
                                p_u_9:datastore_write_creator_data(p_u_30:get_creator_rbxid(), p_u_30:get_creator_name(), function(p41) --[[ Line: 92 ]]
                                    p41:set_received_like_count(p41:get_received_like_count() + 1)
                                end)
                            end)
                            v_u_3:spawn(function() --[[ Line: 98 ]]
                                --[[ Upvalues: (ref 1): v_u_3, (ref 2): p_u_28, (ref 3): p_u_29, (copy 4): p_u_39 ]]
                                v_u_3:wait(5)
                                p_u_28:datastore_player_add_liked_map_no_cooldown(p_u_29, p_u_39)
                            end)
                            v_u_3:spawn(function() --[[ Line: 104 ]]
                                --[[ Upvalues: (ref 1): v_u_3, (ref 2): p_u_9, (ref 3): p_u_29, (copy 4): p_u_39 ]]
                                v_u_3:wait(7.5)
                                p_u_9:get_published_map_manager():datastore_player_write_updated_saved_map_info_to_all_categories(p_u_29, p_u_39)
                            end)
                        end)
                    end)
                    v37:push_back(p_u_29)
                    if v37:count() > 1000 then
                        v37:pop_front()
                    end;
                    return v37:get_table();
                end)
            end)
        end;
        v10.datastore_player_query_has_liked_custom_map_key = function(_, p_u_42, p_u_43, p_u_44) --[[ Name: datastore_player_query_has_liked_custom_map_key ]] --[[ Line: 143 ]]
            --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_5, (copy 3): v_u_26, (copy 4): v_u_24, (copy 5): p_u_8, (ref 6): v_u_23, (ref 7): v_u_1 ]]
            v_u_7:is_int(p_u_42)
            if v_u_5:validate_custom_map_key_components(p_u_43) ~= true then
                return p_u_44(false);
            end;
            if v_u_26:contains(p_u_43) and v_u_26:get(p_u_43):contains(p_u_42) then
                return p_u_44(true);
            end;
            v_u_24:queue_key_request(p_u_42, function() --[[ Line: 153 ]]
                --[[ Upvalues: (ref 1): p_u_8, (ref 2): v_u_23, (copy 3): p_u_43, (ref 4): v_u_1, (ref 5): v_u_26, (copy 6): p_u_44, (copy 7): p_u_42 ]]
                p_u_8._datastore_api:do_datastore_get(v_u_23, string.format("LPID_%s", p_u_43), function(_, p45) --[[ Line: 157 ]]
                    --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_26, (ref 3): p_u_43, (ref 4): p_u_44, (ref 5): p_u_42 ]]
                    local v46 = v_u_1:new(p45 == nil and {} or p45)
                    v_u_26:add(p_u_43, v46)
                    p_u_44(v46:contains(p_u_42))
                end)
            end)
        end;
        local v_u_47 = v_u_2:new()
        local function _(p48) --[[ Name: playerid_to_player_liked_map_list_key ]] --[[ Line: 168 ]]
            return string.format("PlayerLikedMaps_%d", p48);
        end;
        v10.datastore_player_get_liked_map_list = function(p_u_49, p_u_50, p_u_51) --[[ Name: datastore_player_get_liked_map_list ]] --[[ Line: 170 ]]
            --[[ Upvalues: (copy 1): v_u_24 ]]
            v_u_24:queue_key_request(p_u_50, function() --[[ Line: 171 ]]
                --[[ Upvalues: (copy 1): p_u_49, (copy 2): p_u_50, (copy 3): p_u_51 ]]
                p_u_49:datastore_player_get_liked_map_list_no_cooldown(p_u_50, p_u_51)
            end)
        end;
        v10.datastore_player_get_liked_map_list_no_cooldown = function(_, p_u_52, p_u_53) --[[ Name: datastore_player_get_liked_map_list_no_cooldown ]] --[[ Line: 176 ]]
            --[[ Upvalues: (ref 1): v_u_7, (copy 2): v_u_47, (copy 3): p_u_8, (ref 4): v_u_23, (ref 5): v_u_5 ]]
            v_u_7:is_int(p_u_52)
            if v_u_47:contains(p_u_52) then
                return p_u_53(v_u_47:get(p_u_52));
            end;
            p_u_8._datastore_api:do_datastore_get(v_u_23, string.format("PlayerLikedMaps_%d", p_u_52), function(_, p54) --[[ Line: 184 ]]
                --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_47, (copy 3): p_u_52, (copy 4): p_u_53 ]]
                local v55 = v_u_5.SavedMapInfo:info_list_from_datastore_forward_compat_table(p54 == nil and {} or p54)
                v_u_47:add(p_u_52, v55)
                p_u_53(v55)
            end)
        end;
        v10.datastore_player_add_liked_map_no_cooldown = function(p56, p_u_57, p_u_58) --[[ Name: datastore_player_add_liked_map_no_cooldown ]] --[[ Line: 193 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): p_u_8, (ref 3): v_u_23 ]]
            if v_u_5:validate_custom_map_key_components(p_u_58:get_custom_map_data_key()) == true then
                p56:datastore_player_get_liked_map_list_no_cooldown(p_u_57, function(p59) --[[ Line: 195 ]]
                    --[[ Upvalues: (copy 1): p_u_58, (ref 2): p_u_8, (ref 3): v_u_23, (copy 4): p_u_57, (ref 5): v_u_5 ]]
                    for _, v60 in p59:key_itr() do
                        if v60:get_custom_map_data_key() == p_u_58:get_custom_map_data_key() then
                            return;
                        end;
                    end;
                    p59:push_back(p_u_58)
                    if p59:count() > 500 then
                        p59:pop_front()
                    end;
                    p_u_8._datastore_api:do_datastore_set(v_u_23, string.format("PlayerLikedMaps_%d", p_u_57), v_u_5.SavedMapInfo:info_list_to_table(p59))
                end)
            end;
        end;
        p_u_9:register_fn_on_disconnect(function(p61) --[[ Line: 214 ]]
            --[[ Upvalues: (copy 1): v_u_47 ]]
            v_u_47:remove(p61)
        end)
        return v10;
    end
};
