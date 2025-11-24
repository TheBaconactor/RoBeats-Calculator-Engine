-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:22:14 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Server.DebugOut)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPDict)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_5 = require(game.ReplicatedStorage.EditorGame.Data.EditorExportData)
local v_u_6 = require(game.ReplicatedStorage.Shared.APICooldown)
local v_u_7 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_8 = require(game.ReplicatedStorage.Shared.WaitForFinish)
local v_u_9 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_10 = require(game.ReplicatedStorage.PlayerInfo.ArtistEventInfo)
local v_u_11 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
require(game.ReplicatedStorage.Shared.DebugConfig)
local s_DataStoreService_0 = game:GetService("DataStoreService")
return {
    ["new"] = function(_, p_u_12, p_u_13) --[[ Name: new ]] --[[ Line: 19 ]]
        --[[ Upvalues: (copy 1): v_u_7, (copy 2): v_u_5, (copy 3): v_u_1, (copy 4): v_u_4, (copy 5): v_u_8, (copy 6): v_u_10, (copy 7): v_u_2, (copy 8): v_u_9, (copy 9): v_u_3, (copy 10): v_u_11, (copy 11): s_DataStoreService_0, (copy 12): v_u_6 ]]
        local v14 = {}
        local function f_publish_category_get_datastore_key(p15, p16) --[[ Name: publish_category_get_datastore_key ]] --[[ Line: 22 ]]
            --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_5, (ref 3): v_u_1 ]]
            v_u_7:is_enum_member(p15, v_u_5.PublishCategory)
            v_u_7:is_int(p16)
            if p15 == v_u_5.PublishCategory.Global then
                return "GlobalMapList";
            elseif p15 == v_u_5.PublishCategory.SongKey then
                return string.format("SongKeyMapList_%d", p16);
            elseif p15 == v_u_5.PublishCategory.ArtistEvent then
                return string.format("ArtistEventMapList_%d", p16);
            else
                return v_u_1:errf("Invalid publish category (%s)", (tostring(p15)));
            end;
        end;
        local function f_player_validate_saved_map_info(p17, p_u_18, p_u_19) --[[ Name: player_validate_saved_map_info ]] --[[ Line: 36 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): p_u_12 ]]
            local v20, v21, _, _ = v_u_5:validate_custom_map_key_components(p_u_18:get_custom_map_data_key())
            if v20 ~= true then
                return p_u_19(false, string.format("Custom map key is invalid (%s)", p_u_18:get_custom_map_data_key()), p_u_18);
            end;
            if v21 ~= string.lower(p17.Name) then
                return p_u_19(false, string.format("Custom map key does not match player (%s)", p_u_18:get_custom_map_data_key()), p_u_18);
            end;
            p_u_12._editor_game_manager:datastore_player_get_key_custom_map_saved_map_info(p17.UserId, p_u_18:get_custom_map_data_key(), function(p22, p23, p24) --[[ Line: 46 ]]
                --[[ Upvalues: (copy 1): p_u_19, (ref 2): p_u_18, (ref 3): v_u_5 ]]
                if p22 == true then
                    p_u_18 = p24
                    local v25, v26 = v_u_5:saved_map_info_custom_map_data_passes_validation(p_u_18, p23)
                    if v25 == true then
                        return p_u_19(true, "", p_u_18);
                    else
                        return p_u_19(false, v26, p_u_18);
                    end;
                else
                    return p_u_19(false, string.format("Could not find data for custom map key (%s)", p_u_18:get_custom_map_data_key()), p_u_18);
                end;
            end)
        end;
        v14.start = function(p_u_27) --[[ Name: start ]] --[[ Line: 65 ]]
            --[[ Upvalues: (copy 1): p_u_12, (ref 2): v_u_4, (ref 3): v_u_5, (copy 4): f_player_validate_saved_map_info, (ref 5): v_u_8, (copy 6): f_publish_category_get_datastore_key, (ref 7): v_u_10, (ref 8): v_u_7, (ref 9): v_u_2, (ref 10): v_u_9, (copy 11): p_u_13, (ref 12): v_u_3, (ref 13): v_u_1, (ref 14): v_u_11 ]]
            local function f_saved_map_info_list_get_playerid_published_count_and_check_published(p28, p29, p30) --[[ Name: saved_map_info_list_get_playerid_published_count_and_check_published ]] --[[ Line: 67 ]]
                local v31 = 0
                local v32 = false
                for _, v33 in p28:key_itr() do
                    v32 = v33:get_custom_map_data_key() == p30:get_custom_map_data_key() and true or v32
                    if v33:get_creator_rbxid() == p29 then
                        v31 = v31 + 1
                    end;
                end;
                return v31, v32;
            end;
            local function _(p34, p35, p36, p37, p38) --[[ Name: saved_map_info_list_player_saved_map_info_publish_category_check_publish_info_update ]] --[[ Line: 81 ]]
                --[[ Upvalues: (copy 1): f_saved_map_info_list_get_playerid_published_count_and_check_published ]]
                local v39, v40 = f_saved_map_info_list_get_playerid_published_count_and_check_published(p34, p35.UserId, p36)
                p38:set_publish_category_is_published(p37, v40)
                p38:set_publish_category_published_count(p37, v39)
            end;
            p_u_12._evt:wait_on_event(v_u_4.EVT_Editor_CheckPublishInfo_Client, function(p_u_41, p42) --[[ Line: 87 ]]
                --[[ Upvalues: (ref 1): v_u_5, (ref 2): p_u_12, (ref 3): v_u_4, (ref 4): f_player_validate_saved_map_info, (ref 5): v_u_8, (copy 6): p_u_27, (ref 7): f_publish_category_get_datastore_key, (copy 8): f_saved_map_info_list_get_playerid_published_count_and_check_published, (ref 9): v_u_10 ]]
                local function f_response(p43, p44, p45, p46) --[[ Name: response ]] --[[ Line: 88 ]]
                    --[[ Upvalues: (ref 1): v_u_5, (ref 2): p_u_12, (ref 3): v_u_4, (copy 4): p_u_41 ]]
                    if p45 == nil then
                        p45 = v_u_5.CheckPublishInfo:new()
                    end;
                    if p46 == nil then
                        p46 = v_u_5.SavedMapInfo:new()
                    end;
                    p_u_12._evt:fire_event_to_client(v_u_4.EVT_Editor_CheckPublishInfo_Server, p_u_41, p43, p44, p45:to_table(), p46:to_table())
                end;
                f_player_validate_saved_map_info(p_u_41, v_u_5.SavedMapInfo:from_table(p42), function(p47, p48, p_u_49) --[[ Line: 94 ]]
                    --[[ Upvalues: (copy 1): f_response, (ref 2): v_u_8, (ref 3): v_u_5, (ref 4): p_u_27, (copy 5): p_u_41, (ref 6): f_publish_category_get_datastore_key, (ref 7): f_saved_map_info_list_get_playerid_published_count_and_check_published, (ref 8): v_u_10, (ref 9): p_u_12 ]]
                    if p47 ~= true then
                        return f_response(false, p48);
                    end;
                    local v_u_50 = v_u_8.Builder:new()
                    local v_u_51 = v_u_5.CheckPublishInfo:new()
                    v_u_51:set_publish_cost_star_currency(10)
                    p_u_27:lock_playerid_datastore_get_key_map_list_cooldown(p_u_41.UserId, function() --[[ Line: 102 ]]
                        --[[ Upvalues: (copy 1): v_u_50, (ref 2): v_u_5, (ref 3): p_u_27, (ref 4): p_u_41, (ref 5): f_publish_category_get_datastore_key, (copy 6): p_u_49, (copy 7): v_u_51, (ref 8): f_saved_map_info_list_get_playerid_published_count_and_check_published, (ref 9): v_u_10, (ref 10): p_u_12, (ref 11): f_response ]]
                        v_u_50:begin()
                        local l_Global_0 = v_u_5.PublishCategory.Global
                        p_u_27:datastore_player_get_key_map_list_no_cooldown(p_u_41.UserId, f_publish_category_get_datastore_key(l_Global_0, 0), function(p52) --[[ Line: 106 ]]
                            --[[ Upvalues: (ref 1): p_u_41, (ref 2): p_u_49, (copy 3): l_Global_0, (ref 4): v_u_51, (ref 5): f_saved_map_info_list_get_playerid_published_count_and_check_published, (ref 6): v_u_50 ]]
                            local v53 = l_Global_0
                            local v54 = v_u_51
                            local v55, v56 = f_saved_map_info_list_get_playerid_published_count_and_check_published(p52, p_u_41.UserId, p_u_49)
                            v54:set_publish_category_is_published(v53, v56)
                            v54:set_publish_category_published_count(v53, v55)
                            v_u_50:finish()
                        end)
                        v_u_50:begin()
                        local l_SongKey_0 = v_u_5.PublishCategory.SongKey
                        p_u_27:datastore_player_get_key_map_list_no_cooldown(p_u_41.UserId, f_publish_category_get_datastore_key(l_SongKey_0, p_u_49:get_source_songkey()), function(p57) --[[ Line: 115 ]]
                            --[[ Upvalues: (ref 1): p_u_41, (ref 2): p_u_49, (copy 3): l_SongKey_0, (ref 4): v_u_51, (ref 5): f_saved_map_info_list_get_playerid_published_count_and_check_published, (ref 6): v_u_50 ]]
                            local v58 = l_SongKey_0
                            local v59 = v_u_51
                            local v60, v61 = f_saved_map_info_list_get_playerid_published_count_and_check_published(p57, p_u_41.UserId, p_u_49)
                            v59:set_publish_category_is_published(v58, v61)
                            v59:set_publish_category_published_count(v58, v60)
                            v_u_50:finish()
                        end)
                        local v62, v63 = v_u_10:is_event_active(p_u_12._api:get_day_event_list())
                        if v62 == true and v_u_10:get_playable_song_set(v63):contains(p_u_49:get_source_songkey()) == true then
                            v_u_50:begin()
                            local l_ArtistEvent_0 = v_u_5.PublishCategory.ArtistEvent
                            p_u_27:datastore_player_get_key_map_list_no_cooldown(p_u_41.UserId, f_publish_category_get_datastore_key(l_ArtistEvent_0, v63), function(p64) --[[ Line: 126 ]]
                                --[[ Upvalues: (ref 1): p_u_41, (ref 2): p_u_49, (copy 3): l_ArtistEvent_0, (ref 4): v_u_51, (ref 5): f_saved_map_info_list_get_playerid_published_count_and_check_published, (ref 6): v_u_50 ]]
                                local v65 = l_ArtistEvent_0
                                local v66 = v_u_51
                                local v67, v68 = f_saved_map_info_list_get_playerid_published_count_and_check_published(p64, p_u_41.UserId, p_u_49)
                                v66:set_publish_category_is_published(v65, v68)
                                v66:set_publish_category_published_count(v65, v67)
                                v_u_50:finish()
                            end)
                        end;
                        v_u_50:wait_for_finish(function() --[[ Line: 133 ]]
                            --[[ Upvalues: (ref 1): f_response, (ref 2): v_u_51, (ref 3): p_u_49 ]]
                            f_response(true, "", v_u_51, p_u_49)
                        end)
                    end)
                end)
            end)
            p_u_12._evt:wait_on_event(v_u_4.EVT_Editor_GetPublishedMaps_Client, function(p_u_69, p70, p71) --[[ Line: 140 ]]
                --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_5, (ref 3): v_u_2, (ref 4): p_u_12, (ref 5): v_u_4, (ref 6): v_u_9, (ref 7): v_u_10, (ref 8): p_u_13, (copy 9): p_u_27, (ref 10): f_publish_category_get_datastore_key, (ref 11): v_u_3, (ref 12): v_u_1 ]]
                v_u_7:is_enum_member(p70, v_u_5.PublishCategory)
                v_u_7:is_int(p71)
                local function f_response(p72) --[[ Name: response ]] --[[ Line: 144 ]]
                    --[[ Upvalues: (ref 1): v_u_2, (ref 2): p_u_12, (ref 3): v_u_4, (copy 4): p_u_69, (ref 5): v_u_5 ]]
                    if p72 == nil then
                        p72 = v_u_2:new()
                    end;
                    p_u_12._evt:fire_event_to_client(v_u_4.EVT_Editor_GetPublishedMaps_Server, p_u_69, v_u_5.SavedMapInfo:info_list_to_table(p72))
                end;
                if p70 ~= v_u_5.PublishCategory.Global then
                    if p70 == v_u_5.PublishCategory.SongKey then
                        v_u_7:is_true(v_u_9:singleton():contains_key(p71))
                    elseif p70 == v_u_5.PublishCategory.ArtistEvent then
                        local v73
                        v73, p71 = v_u_10:is_event_active(p_u_12._api:get_day_event_list())
                        if v73 ~= true then
                            return f_response();
                        end;
                    elseif p70 == v_u_5.PublishCategory.MyLikedMaps then
                        p_u_13:get_map_likes_manager():datastore_player_get_liked_map_list(p_u_69.UserId, function(p74) --[[ Line: 160 ]]
                            --[[ Upvalues: (ref 1): v_u_2, (ref 2): p_u_12, (ref 3): v_u_4, (copy 4): p_u_69, (ref 5): v_u_5 ]]
                            if p74 == nil then
                                p74 = v_u_2:new()
                            end;
                            p_u_12._evt:fire_event_to_client(v_u_4.EVT_Editor_GetPublishedMaps_Server, p_u_69, v_u_5.SavedMapInfo:info_list_to_table(p74))
                        end)
                        return;
                    end;
                end;
                p_u_27:datastore_player_get_key_map_list(p_u_69.UserId, f_publish_category_get_datastore_key(p70, p71), function(p75) --[[ Line: 166 ]]
                    --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_2, (ref 3): v_u_3, (ref 4): v_u_1, (ref 5): p_u_12, (ref 6): v_u_4, (copy 7): p_u_69 ]]
                    local v76 = v_u_5.SavedMapInfo:info_list_from_table(v_u_5.SavedMapInfo:info_list_to_table(p75))
                    v_u_2:remove_if(v76, function(p77) --[[ Line: 168 ]]
                        --[[ Upvalues: (ref 1): v_u_5 ]]
                        return v_u_5:validate_saved_map_info(p77) ~= true;
                    end)
                    local v78 = v_u_5.SavedMapInfo:info_list_to_table(v76)
                    if v_u_3:is_dev_build() then
                        v_u_1:puts("EVT_Editor_GetPublishedMaps_Client")
                        print(v78)
                    end;
                    p_u_12._evt:fire_event_to_client(v_u_4.EVT_Editor_GetPublishedMaps_Server, p_u_69, v78)
                end)
            end)
            local function _(p79, p_u_80) --[[ Name: saved_map_info_list_remove_saved_map_info ]] --[[ Line: 180 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                v_u_2:remove_if(p79, function(p81) --[[ Line: 181 ]]
                    --[[ Upvalues: (copy 1): p_u_80 ]]
                    return p81:get_custom_map_data_key() == p_u_80:get_custom_map_data_key();
                end)
            end;
            local function _(p_u_82, p_u_83, p_u_84) --[[ Name: do_publish_saved_map_info ]] --[[ Line: 187 ]]
                --[[ Upvalues: (ref 1): v_u_8, (ref 2): v_u_5, (copy 3): p_u_27, (ref 4): v_u_2, (copy 5): f_saved_map_info_list_get_playerid_published_count_and_check_published, (ref 6): f_publish_category_get_datastore_key, (ref 7): v_u_10, (ref 8): p_u_12 ]]
                local v_u_85 = v_u_8.Builder:new()
                local v_u_86 = v_u_5.CheckPublishInfo:new()
                p_u_27:lock_playerid_datastore_update_key_map_list_cooldown(p_u_82.UserId, function() --[[ Line: 191 ]]
                    --[[ Upvalues: (copy 1): v_u_85, (ref 2): p_u_27, (copy 3): p_u_82, (copy 4): p_u_83, (ref 5): v_u_2, (copy 6): v_u_86, (ref 7): f_saved_map_info_list_get_playerid_published_count_and_check_published, (ref 8): f_publish_category_get_datastore_key, (ref 9): v_u_5, (ref 10): v_u_10, (ref 11): p_u_12, (copy 12): p_u_84 ]]
                    local function f_publish_key_into_category(p87, p_u_88) --[[ Name: publish_key_into_category ]] --[[ Line: 193 ]]
                        --[[ Upvalues: (ref 1): v_u_85, (ref 2): p_u_27, (ref 3): p_u_82, (ref 4): p_u_83, (ref 5): v_u_2, (ref 6): v_u_86, (ref 7): f_saved_map_info_list_get_playerid_published_count_and_check_published ]]
                        v_u_85:begin()
                        p_u_27:datastore_player_update_key_map_list_no_cooldown(p_u_82.UserId, p87, function(p89) --[[ Line: 198 ]]
                            --[[ Upvalues: (ref 1): p_u_83, (ref 2): v_u_2, (ref 3): p_u_82, (copy 4): p_u_88, (ref 5): v_u_86, (ref 6): f_saved_map_info_list_get_playerid_published_count_and_check_published ]]
                            local v_u_90 = p_u_83
                            v_u_2:remove_if(p89, function(p91) --[[ Line: 181 ]]
                                --[[ Upvalues: (copy 1): v_u_90 ]]
                                return p91:get_custom_map_data_key() == v_u_90:get_custom_map_data_key();
                            end)
                            p89:push_back(p_u_83)
                            if p89:count() > 500 then
                                p89:pop_front()
                            end;
                            local v92 = p_u_88
                            local v93 = v_u_86
                            local v94, v95 = f_saved_map_info_list_get_playerid_published_count_and_check_published(p89, p_u_82.UserId, p_u_83)
                            v93:set_publish_category_is_published(v92, v95)
                            v93:set_publish_category_published_count(v92, v94)
                        end, function() --[[ Line: 207 ]]
                            --[[ Upvalues: (ref 1): v_u_85 ]]
                            v_u_85:finish()
                        end)
                    end;
                    f_publish_key_into_category(f_publish_category_get_datastore_key(v_u_5.PublishCategory.Global, 0), v_u_5.PublishCategory.Global)
                    f_publish_key_into_category(f_publish_category_get_datastore_key(v_u_5.PublishCategory.SongKey, p_u_83:get_source_songkey()), v_u_5.PublishCategory.SongKey)
                    local v96, v97 = v_u_10:is_event_active(p_u_12._api:get_day_event_list())
                    if v96 == true and v_u_10:get_playable_song_set(v97):contains(p_u_83:get_source_songkey()) == true then
                        f_publish_key_into_category(f_publish_category_get_datastore_key(v_u_5.PublishCategory.ArtistEvent, v97), v_u_5.PublishCategory.ArtistEvent)
                    end;
                    v_u_85:wait_for_finish(function() --[[ Line: 233 ]]
                        --[[ Upvalues: (ref 1): p_u_84, (ref 2): v_u_86 ]]
                        p_u_84(v_u_86)
                    end)
                end)
            end;
            p_u_12._evt:wait_on_event(v_u_4.EVT_Editor_PublishCustomMap_Client, function(p_u_98, p99) --[[ Line: 239 ]]
                --[[ Upvalues: (ref 1): v_u_5, (ref 2): p_u_12, (ref 3): v_u_4, (ref 4): f_player_validate_saved_map_info, (ref 5): v_u_11, (ref 6): v_u_8, (copy 7): p_u_27, (ref 8): v_u_2, (copy 9): f_saved_map_info_list_get_playerid_published_count_and_check_published, (ref 10): f_publish_category_get_datastore_key, (ref 11): v_u_10, (ref 12): p_u_13 ]]
                local function f_response(p100, p101, p102) --[[ Name: response ]] --[[ Line: 240 ]]
                    --[[ Upvalues: (ref 1): v_u_5, (ref 2): p_u_12, (ref 3): v_u_4, (copy 4): p_u_98 ]]
                    if p102 == nil then
                        p102 = v_u_5.CheckPublishInfo:new()
                    end;
                    p_u_12._evt:fire_event_to_client(v_u_4.EVT_Editor_PublishCustomMap_Server, p_u_98, p100, p101, p102:to_table())
                end;
                f_player_validate_saved_map_info(p_u_98, v_u_5.SavedMapInfo:from_table(p99), function(p103, p104, p_u_105) --[[ Line: 245 ]]
                    --[[ Upvalues: (copy 1): f_response, (ref 2): p_u_12, (copy 3): p_u_98, (ref 4): v_u_11, (ref 5): v_u_5, (ref 6): v_u_4, (ref 7): v_u_8, (ref 8): p_u_27, (ref 9): v_u_2, (ref 10): f_saved_map_info_list_get_playerid_published_count_and_check_published, (ref 11): f_publish_category_get_datastore_key, (ref 12): v_u_10, (ref 13): p_u_13 ]]
                    if p103 ~= true then
                        return f_response(false, p104);
                    end;
                    p_u_12._player_blob_manager:get_verified_cached_blob(p_u_98.UserId, function(p106) --[[ Line: 249 ]]
                        --[[ Upvalues: (ref 1): v_u_11, (ref 2): f_response, (ref 3): p_u_12, (ref 4): p_u_98, (copy 5): p_u_105, (ref 6): v_u_5, (ref 7): v_u_4, (ref 8): v_u_8, (ref 9): p_u_27, (ref 10): v_u_2, (ref 11): f_saved_map_info_list_get_playerid_published_count_and_check_published, (ref 12): f_publish_category_get_datastore_key, (ref 13): v_u_10, (ref 14): p_u_13 ]]
                        local l_Stars_0 = v_u_11.CurrencyType.Stars
                        local v107 = v_u_11:get_currency_type_amount(p106, l_Stars_0)
                        if v107 < 10 then
                            return f_response(false, string.format("Not enough stars to publish this map."));
                        end;
                        v_u_11:set_currency_type_amount(p106, l_Stars_0, v107 - 10)
                        p_u_12._player_blob_manager:enqueue_blob_sync_request(p_u_98.UserId, v_u_11.PlayerBlobRequestType.Write, function() --[[ Line: 263 ]]
                            --[[ Upvalues: (ref 1): p_u_98, (ref 2): p_u_105, (ref 3): v_u_5, (ref 4): p_u_12, (ref 5): v_u_4, (ref 6): v_u_8, (ref 7): p_u_27, (ref 8): v_u_2, (ref 9): f_saved_map_info_list_get_playerid_published_count_and_check_published, (ref 10): f_publish_category_get_datastore_key, (ref 11): v_u_10, (ref 12): p_u_13 ]]
                            local function _() --[[ Name: do_publish ]] --[[ Line: 264 ]]
                                --[[ Upvalues: (ref 1): p_u_98, (ref 2): p_u_105, (ref 3): v_u_5, (ref 4): p_u_12, (ref 5): v_u_4, (ref 6): v_u_8, (ref 7): p_u_27, (ref 8): v_u_2, (ref 9): f_saved_map_info_list_get_playerid_published_count_and_check_published, (ref 10): f_publish_category_get_datastore_key, (ref 11): v_u_10 ]]
                                local v_u_108 = p_u_98
                                local v_u_109 = p_u_105
                                local function v_u_111(p110) --[[ Line: 265 ]]
                                    --[[ Upvalues: (ref 1): v_u_5, (ref 2): p_u_12, (ref 3): v_u_4, (ref 4): p_u_98 ]]
                                    if p110 == nil then
                                        p110 = v_u_5.CheckPublishInfo:new()
                                    end;
                                    p_u_12._evt:fire_event_to_client(v_u_4.EVT_Editor_PublishCustomMap_Server, p_u_98, true, "", p110:to_table())
                                end;
                                local v_u_112 = v_u_8.Builder:new()
                                local v_u_113 = v_u_5.CheckPublishInfo:new()
                                p_u_27:lock_playerid_datastore_update_key_map_list_cooldown(v_u_108.UserId, function() --[[ Line: 191 ]]
                                    --[[ Upvalues: (copy 1): v_u_112, (ref 2): p_u_27, (copy 3): v_u_108, (copy 4): v_u_109, (ref 5): v_u_2, (copy 6): v_u_113, (ref 7): f_saved_map_info_list_get_playerid_published_count_and_check_published, (ref 8): f_publish_category_get_datastore_key, (ref 9): v_u_5, (ref 10): v_u_10, (ref 11): p_u_12, (copy 12): v_u_111 ]]
                                    local function f_publish_key_into_category(p114, p_u_115) --[[ Name: publish_key_into_category ]] --[[ Line: 193 ]]
                                        --[[ Upvalues: (ref 1): v_u_112, (ref 2): p_u_27, (ref 3): v_u_108, (ref 4): v_u_109, (ref 5): v_u_2, (ref 6): v_u_113, (ref 7): f_saved_map_info_list_get_playerid_published_count_and_check_published ]]
                                        v_u_112:begin()
                                        p_u_27:datastore_player_update_key_map_list_no_cooldown(v_u_108.UserId, p114, function(p116) --[[ Line: 198 ]]
                                            --[[ Upvalues: (ref 1): v_u_109, (ref 2): v_u_2, (ref 3): v_u_108, (copy 4): p_u_115, (ref 5): v_u_113, (ref 6): f_saved_map_info_list_get_playerid_published_count_and_check_published ]]
                                            local v_u_117 = v_u_109
                                            v_u_2:remove_if(p116, function(p118) --[[ Line: 181 ]]
                                                --[[ Upvalues: (copy 1): v_u_117 ]]
                                                return p118:get_custom_map_data_key() == v_u_117:get_custom_map_data_key();
                                            end)
                                            p116:push_back(v_u_109)
                                            if p116:count() > 500 then
                                                p116:pop_front()
                                            end;
                                            local v119 = p_u_115
                                            local v120 = v_u_113
                                            local v121, v122 = f_saved_map_info_list_get_playerid_published_count_and_check_published(p116, v_u_108.UserId, v_u_109)
                                            v120:set_publish_category_is_published(v119, v122)
                                            v120:set_publish_category_published_count(v119, v121)
                                        end, function() --[[ Line: 207 ]]
                                            --[[ Upvalues: (ref 1): v_u_112 ]]
                                            v_u_112:finish()
                                        end)
                                    end;
                                    f_publish_key_into_category(f_publish_category_get_datastore_key(v_u_5.PublishCategory.Global, 0), v_u_5.PublishCategory.Global)
                                    f_publish_key_into_category(f_publish_category_get_datastore_key(v_u_5.PublishCategory.SongKey, v_u_109:get_source_songkey()), v_u_5.PublishCategory.SongKey)
                                    local v123, v124 = v_u_10:is_event_active(p_u_12._api:get_day_event_list())
                                    if v123 == true and v_u_10:get_playable_song_set(v124):contains(v_u_109:get_source_songkey()) == true then
                                        f_publish_key_into_category(f_publish_category_get_datastore_key(v_u_5.PublishCategory.ArtistEvent, v124), v_u_5.PublishCategory.ArtistEvent)
                                    end;
                                    v_u_112:wait_for_finish(function() --[[ Line: 233 ]]
                                        --[[ Upvalues: (ref 1): v_u_111, (ref 2): v_u_113 ]]
                                        v_u_111(v_u_113)
                                    end)
                                end)
                            end;
                            if v_u_5:validate_custom_map_key_components(p_u_105:get_custom_map_data_key()) == true then
                                p_u_13:datastore_get_editable_saved_map_info_given_custom_map_data_key_no_cooldown(p_u_105:get_custom_map_data_key(), function(p125) --[[ Line: 272 ]]
                                    --[[ Upvalues: (ref 1): v_u_5, (ref 2): p_u_105, (ref 3): p_u_98, (ref 4): p_u_12, (ref 5): v_u_4, (ref 6): v_u_8, (ref 7): p_u_27, (ref 8): v_u_2, (ref 9): f_saved_map_info_list_get_playerid_published_count_and_check_published, (ref 10): f_publish_category_get_datastore_key, (ref 11): v_u_10 ]]
                                    v_u_5.SavedMapInfo:write_editable_saved_map_info_from_src_to_dest(p125, p_u_105)
                                    local v_u_126 = p_u_98
                                    local v_u_127 = p_u_105
                                    local function v_u_129(p128) --[[ Line: 265 ]]
                                        --[[ Upvalues: (ref 1): v_u_5, (ref 2): p_u_12, (ref 3): v_u_4, (ref 4): p_u_98 ]]
                                        if p128 == nil then
                                            p128 = v_u_5.CheckPublishInfo:new()
                                        end;
                                        p_u_12._evt:fire_event_to_client(v_u_4.EVT_Editor_PublishCustomMap_Server, p_u_98, true, "", p128:to_table())
                                    end;
                                    local v_u_130 = v_u_8.Builder:new()
                                    local v_u_131 = v_u_5.CheckPublishInfo:new()
                                    p_u_27:lock_playerid_datastore_update_key_map_list_cooldown(v_u_126.UserId, function() --[[ Line: 191 ]]
                                        --[[ Upvalues: (copy 1): v_u_130, (ref 2): p_u_27, (copy 3): v_u_126, (copy 4): v_u_127, (ref 5): v_u_2, (copy 6): v_u_131, (ref 7): f_saved_map_info_list_get_playerid_published_count_and_check_published, (ref 8): f_publish_category_get_datastore_key, (ref 9): v_u_5, (ref 10): v_u_10, (ref 11): p_u_12, (copy 12): v_u_129 ]]
                                        local function f_publish_key_into_category(p132, p_u_133) --[[ Name: publish_key_into_category ]] --[[ Line: 193 ]]
                                            --[[ Upvalues: (ref 1): v_u_130, (ref 2): p_u_27, (ref 3): v_u_126, (ref 4): v_u_127, (ref 5): v_u_2, (ref 6): v_u_131, (ref 7): f_saved_map_info_list_get_playerid_published_count_and_check_published ]]
                                            v_u_130:begin()
                                            p_u_27:datastore_player_update_key_map_list_no_cooldown(v_u_126.UserId, p132, function(p134) --[[ Line: 198 ]]
                                                --[[ Upvalues: (ref 1): v_u_127, (ref 2): v_u_2, (ref 3): v_u_126, (copy 4): p_u_133, (ref 5): v_u_131, (ref 6): f_saved_map_info_list_get_playerid_published_count_and_check_published ]]
                                                local v_u_135 = v_u_127
                                                v_u_2:remove_if(p134, function(p136) --[[ Line: 181 ]]
                                                    --[[ Upvalues: (copy 1): v_u_135 ]]
                                                    return p136:get_custom_map_data_key() == v_u_135:get_custom_map_data_key();
                                                end)
                                                p134:push_back(v_u_127)
                                                if p134:count() > 500 then
                                                    p134:pop_front()
                                                end;
                                                local v137 = p_u_133
                                                local v138 = v_u_131
                                                local v139, v140 = f_saved_map_info_list_get_playerid_published_count_and_check_published(p134, v_u_126.UserId, v_u_127)
                                                v138:set_publish_category_is_published(v137, v140)
                                                v138:set_publish_category_published_count(v137, v139)
                                            end, function() --[[ Line: 207 ]]
                                                --[[ Upvalues: (ref 1): v_u_130 ]]
                                                v_u_130:finish()
                                            end)
                                        end;
                                        f_publish_key_into_category(f_publish_category_get_datastore_key(v_u_5.PublishCategory.Global, 0), v_u_5.PublishCategory.Global)
                                        f_publish_key_into_category(f_publish_category_get_datastore_key(v_u_5.PublishCategory.SongKey, v_u_127:get_source_songkey()), v_u_5.PublishCategory.SongKey)
                                        local v141, v142 = v_u_10:is_event_active(p_u_12._api:get_day_event_list())
                                        if v141 == true and v_u_10:get_playable_song_set(v142):contains(v_u_127:get_source_songkey()) == true then
                                            f_publish_key_into_category(f_publish_category_get_datastore_key(v_u_5.PublishCategory.ArtistEvent, v142), v_u_5.PublishCategory.ArtistEvent)
                                        end;
                                        v_u_130:wait_for_finish(function() --[[ Line: 233 ]]
                                            --[[ Upvalues: (ref 1): v_u_129, (ref 2): v_u_131 ]]
                                            v_u_129(v_u_131)
                                        end)
                                    end)
                                end)
                            else
                                local v_u_143 = p_u_98
                                local v_u_144 = p_u_105
                                local function v_u_146(p145) --[[ Line: 265 ]]
                                    --[[ Upvalues: (ref 1): v_u_5, (ref 2): p_u_12, (ref 3): v_u_4, (ref 4): p_u_98 ]]
                                    if p145 == nil then
                                        p145 = v_u_5.CheckPublishInfo:new()
                                    end;
                                    p_u_12._evt:fire_event_to_client(v_u_4.EVT_Editor_PublishCustomMap_Server, p_u_98, true, "", p145:to_table())
                                end;
                                local v_u_147 = v_u_8.Builder:new()
                                local v_u_148 = v_u_5.CheckPublishInfo:new()
                                p_u_27:lock_playerid_datastore_update_key_map_list_cooldown(v_u_143.UserId, function() --[[ Line: 191 ]]
                                    --[[ Upvalues: (copy 1): v_u_147, (ref 2): p_u_27, (copy 3): v_u_143, (copy 4): v_u_144, (ref 5): v_u_2, (copy 6): v_u_148, (ref 7): f_saved_map_info_list_get_playerid_published_count_and_check_published, (ref 8): f_publish_category_get_datastore_key, (ref 9): v_u_5, (ref 10): v_u_10, (ref 11): p_u_12, (copy 12): v_u_146 ]]
                                    local function f_publish_key_into_category(p149, p_u_150) --[[ Name: publish_key_into_category ]] --[[ Line: 193 ]]
                                        --[[ Upvalues: (ref 1): v_u_147, (ref 2): p_u_27, (ref 3): v_u_143, (ref 4): v_u_144, (ref 5): v_u_2, (ref 6): v_u_148, (ref 7): f_saved_map_info_list_get_playerid_published_count_and_check_published ]]
                                        v_u_147:begin()
                                        p_u_27:datastore_player_update_key_map_list_no_cooldown(v_u_143.UserId, p149, function(p151) --[[ Line: 198 ]]
                                            --[[ Upvalues: (ref 1): v_u_144, (ref 2): v_u_2, (ref 3): v_u_143, (copy 4): p_u_150, (ref 5): v_u_148, (ref 6): f_saved_map_info_list_get_playerid_published_count_and_check_published ]]
                                            local v_u_152 = v_u_144
                                            v_u_2:remove_if(p151, function(p153) --[[ Line: 181 ]]
                                                --[[ Upvalues: (copy 1): v_u_152 ]]
                                                return p153:get_custom_map_data_key() == v_u_152:get_custom_map_data_key();
                                            end)
                                            p151:push_back(v_u_144)
                                            if p151:count() > 500 then
                                                p151:pop_front()
                                            end;
                                            local v154 = p_u_150
                                            local v155 = v_u_148
                                            local v156, v157 = f_saved_map_info_list_get_playerid_published_count_and_check_published(p151, v_u_143.UserId, v_u_144)
                                            v155:set_publish_category_is_published(v154, v157)
                                            v155:set_publish_category_published_count(v154, v156)
                                        end, function() --[[ Line: 207 ]]
                                            --[[ Upvalues: (ref 1): v_u_147 ]]
                                            v_u_147:finish()
                                        end)
                                    end;
                                    f_publish_key_into_category(f_publish_category_get_datastore_key(v_u_5.PublishCategory.Global, 0), v_u_5.PublishCategory.Global)
                                    f_publish_key_into_category(f_publish_category_get_datastore_key(v_u_5.PublishCategory.SongKey, v_u_144:get_source_songkey()), v_u_5.PublishCategory.SongKey)
                                    local v158, v159 = v_u_10:is_event_active(p_u_12._api:get_day_event_list())
                                    if v158 == true and v_u_10:get_playable_song_set(v159):contains(v_u_144:get_source_songkey()) == true then
                                        f_publish_key_into_category(f_publish_category_get_datastore_key(v_u_5.PublishCategory.ArtistEvent, v159), v_u_5.PublishCategory.ArtistEvent)
                                    end;
                                    v_u_147:wait_for_finish(function() --[[ Line: 233 ]]
                                        --[[ Upvalues: (ref 1): v_u_146, (ref 2): v_u_148 ]]
                                        v_u_146(v_u_148)
                                    end)
                                end)
                            end;
                        end)
                    end)
                end)
            end)
        end;
        v14.datastore_player_write_updated_saved_map_info_to_all_categories = function(p160, p161, p_u_162) --[[ Name: datastore_player_write_updated_saved_map_info_to_all_categories ]] --[[ Line: 286 ]]
            --[[ Upvalues: (copy 1): f_publish_category_get_datastore_key, (ref 2): v_u_5, (ref 3): v_u_10, (copy 4): p_u_12 ]]
            local function f_fn_replace_saved_map_info_if_match_found(p163) --[[ Name: fn_replace_saved_map_info_if_match_found ]] --[[ Line: 287 ]]
                --[[ Upvalues: (copy 1): p_u_162 ]]
                local v164 = false
                for v165 = 1, p163:count() do
                    if p163:get(v165):get_custom_map_data_key() == p_u_162:get_custom_map_data_key() then
                        p163:set(v165, p_u_162)
                        v164 = true
                        break;
                    end;
                end;
                if v164 == false then
                    return false;
                end;
            end;
            p160:datastore_player_update_key_map_list_no_cooldown(p161, f_publish_category_get_datastore_key(v_u_5.PublishCategory.Global, 0), f_fn_replace_saved_map_info_if_match_found)
            p160:datastore_player_update_key_map_list_no_cooldown(p161, f_publish_category_get_datastore_key(v_u_5.PublishCategory.SongKey, p_u_162:get_source_songkey()), f_fn_replace_saved_map_info_if_match_found)
            local v166, v167 = v_u_10:is_event_active(p_u_12._api:get_day_event_list())
            if v166 == true and v_u_10:get_playable_song_set(v167):contains(p_u_162:get_source_songkey()) == true then
                p160:datastore_player_update_key_map_list_no_cooldown(p161, f_publish_category_get_datastore_key(v_u_5.PublishCategory.ArtistEvent, v167), f_fn_replace_saved_map_info_if_match_found)
            end;
        end;
        local v_u_168 = nil
        v_u_3:ptry(function() --[[ Line: 329 ]]
            --[[ Upvalues: (ref 1): v_u_168, (ref 2): s_DataStoreService_0 ]]
            v_u_168 = s_DataStoreService_0:GetDataStore("EditorGamePublishedMapList")
        end)
        local v_u_169 = v_u_6:new():set_cooldown(0.5)
        local v_u_170 = v_u_6:new():set_cooldown(4)
        v14.datastore_player_get_key_map_list_no_cooldown = function(_, _, p171, p_u_172) --[[ Name: datastore_player_get_key_map_list_no_cooldown ]] --[[ Line: 335 ]]
            --[[ Upvalues: (copy 1): p_u_12, (ref 2): v_u_168, (ref 3): v_u_5, (ref 4): v_u_2 ]]
            p_u_12._datastore_api:do_datastore_get(v_u_168, p171, function(p173, p174) --[[ Line: 336 ]]
                --[[ Upvalues: (copy 1): p_u_172, (ref 2): v_u_5, (ref 3): v_u_2 ]]
                if p173 and typeof(p174) == "table" then
                    p_u_172(v_u_5.SavedMapInfo:info_list_from_datastore_forward_compat_table(p174))
                else
                    p_u_172(v_u_2:new())
                end;
            end)
        end;
        v14.lock_playerid_datastore_get_key_map_list_cooldown = function(_, p175, p_u_176) --[[ Name: lock_playerid_datastore_get_key_map_list_cooldown ]] --[[ Line: 345 ]]
            --[[ Upvalues: (copy 1): v_u_169 ]]
            v_u_169:queue_key_request(p175, function() --[[ Line: 346 ]]
                --[[ Upvalues: (copy 1): p_u_176 ]]
                p_u_176()
            end)
        end;
        v14.datastore_player_get_key_map_list = function(p_u_177, p_u_178, p_u_179, p_u_180) --[[ Name: datastore_player_get_key_map_list ]] --[[ Line: 351 ]]
            --[[ Upvalues: (ref 1): v_u_7 ]]
            v_u_7:is_string(p_u_179)
            v_u_7:is_int(p_u_178)
            p_u_177:lock_playerid_datastore_get_key_map_list_cooldown(p_u_178, function() --[[ Line: 355 ]]
                --[[ Upvalues: (copy 1): p_u_177, (copy 2): p_u_178, (copy 3): p_u_179, (copy 4): p_u_180 ]]
                p_u_177:datastore_player_get_key_map_list_no_cooldown(p_u_178, p_u_179, p_u_180)
            end)
        end;
        v14.datastore_player_update_key_map_list_no_cooldown = function(_, _, p181, p_u_182, p_u_183) --[[ Name: datastore_player_update_key_map_list_no_cooldown ]] --[[ Line: 360 ]]
            --[[ Upvalues: (copy 1): p_u_12, (ref 2): v_u_168, (ref 3): v_u_5, (ref 4): v_u_2 ]]
            p_u_12._datastore_api:do_datastore_update(v_u_168, p181, function(p184) --[[ Line: 361 ]]
                --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_2, (copy 3): p_u_182 ]]
                local v185 = v_u_5.SavedMapInfo:info_list_from_datastore_forward_compat_table(p184 == nil and {} or p184)
                v_u_2:remove_if(v185, function(p186) --[[ Line: 365 ]]
                    --[[ Upvalues: (ref 1): v_u_5 ]]
                    return v_u_5:validate_saved_map_info(p186) ~= true;
                end)
                if p_u_182(v185) == false then
                    return nil;
                else
                    return v_u_5.SavedMapInfo:info_list_to_table(v185);
                end;
            end, function() --[[ Line: 376 ]]
                --[[ Upvalues: (copy 1): p_u_183 ]]
                if p_u_183 then
                    p_u_183()
                end;
            end)
        end;
        v14.lock_playerid_datastore_update_key_map_list_cooldown = function(_, p187, p_u_188) --[[ Name: lock_playerid_datastore_update_key_map_list_cooldown ]] --[[ Line: 381 ]]
            --[[ Upvalues: (copy 1): v_u_170 ]]
            v_u_170:queue_key_request(p187, function() --[[ Line: 382 ]]
                --[[ Upvalues: (copy 1): p_u_188 ]]
                p_u_188()
            end)
        end;
        return v14;
    end
};
