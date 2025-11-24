-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:23 PM
-- Time elapsed: 14 milliseconds

local v_u_1 = require(game.ReplicatedStorage.Server.DebugOut)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_4 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Server.ServerAPIManager)
require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
require(game.ReplicatedStorage.Shared.AssertType)
require(game.ReplicatedStorage.Shared.LeaderboardSongInfo)
local v_u_6 = require(game.ReplicatedStorage.Shared.WaitForFinish)
local v_u_7 = require(game.ReplicatedStorage.Shared.APICooldown)
require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_8 = require(game.ReplicatedStorage.Shared.PlayerSongStatCollection)
local v_u_9 = require(game.ReplicatedStorage.Shared.PlayerSongPlay)
local s_DataStoreService_0 = game:GetService("DataStoreService")
local s_HttpService_0 = game:GetService("HttpService")
return {
    ["new"] = function(_, p_u_10) --[[ Name: new ]] --[[ Line: 22 ]]
        --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_8, (copy 3): v_u_5, (copy 4): v_u_1, (copy 5): s_HttpService_0, (copy 6): v_u_6, (copy 7): v_u_2, (copy 8): v_u_9, (copy 9): v_u_3, (copy 10): v_u_7, (copy 11): s_DataStoreService_0 ]]
        local v_u_11 = {}
        v_u_11.dsapi_player_song_stats_get = function(p_u_12, p_u_13, p_u_14) --[[ Name: dsapi_player_song_stats_get ]] --[[ Line: 25 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): p_u_10, (ref 3): v_u_8, (ref 4): v_u_5, (ref 5): v_u_1, (ref 6): s_HttpService_0 ]]
            if v_u_4.PlayerSongStatDoWebAPIRead == true then
                p_u_10._api:api_player_song_stats_get(p_u_13, function(p15, p16) --[[ Line: 27 ]]
                    --[[ Upvalues: (copy 1): p_u_14, (ref 2): v_u_4, (ref 3): v_u_8, (copy 4): p_u_12, (copy 5): p_u_13, (ref 6): v_u_5, (ref 7): v_u_1 ]]
                    p_u_14(p15, p16)
                    if v_u_4.PlayerSongStatTempWriteFromWebToDatastore == true then
                        local v17 = v_u_8:new()
                        v17:load_from_json_obj(p16)
                        p_u_12:datastore_set_player_song_stat_collection(p_u_13, v17, function() --[[ Line: 33 ]]
                            --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_1, (ref 3): p_u_13 ]]
                            if v_u_5:is_dev_build() then
                                v_u_1:puts("PlayerSongStatTempWriteFromWebToDatastore wrote playerid(%d) PSSC to datastore", p_u_13)
                            end;
                        end)
                    end;
                end)
            end;
            if v_u_4.PlayerSongStatDoDatastoreAPIRead == true then
                p_u_12:datastore_get_player_song_stat_collection(p_u_13, function(p18) --[[ Line: 43 ]]
                    --[[ Upvalues: (ref 1): s_HttpService_0, (copy 2): p_u_14 ]]
                    local v19 = p18:to_json_obj()
                    p_u_14(s_HttpService_0:JSONEncode(v19), v19)
                end)
            end;
        end;
        v_u_11.dsapi_player_song_stats_get_rank = function(p20, p_u_21, p_u_22, p_u_23) --[[ Name: dsapi_player_song_stats_get_rank ]] --[[ Line: 51 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): p_u_10, (ref 3): s_HttpService_0 ]]
            if v_u_4.PlayerSongStatDoWebAPIRead == true then
                p_u_10._api:api_player_song_stats_get_rank(p_u_21, p_u_22, function(p24, p25) --[[ Line: 53 ]]
                    --[[ Upvalues: (copy 1): p_u_23 ]]
                    p_u_23(p24, p25)
                end)
            end;
            if v_u_4.PlayerSongStatDoDatastoreAPIRead == true then
                p20:datastore_get_songkey_top_scores_play_list_no_cooldown(p_u_22, function(p26) --[[ Line: 59 ]]
                    --[[ Upvalues: (copy 1): p_u_21, (copy 2): p_u_22, (ref 3): s_HttpService_0, (copy 4): p_u_23 ]]
                    local v27 = 0
                    for v28, v29 in p26:key_itr() do
                        if v29:get_rbxid() == p_u_21 then
                            v27 = v28
                            break;
                        end;
                    end;
                    local v30 = {
                        ["SongKey"] = p_u_22,
                        ["Rank"] = v27,
                        ["TotalCount"] = p26:count()
                    }
                    p_u_23(s_HttpService_0:JSONEncode(v30), v30)
                end)
            end;
        end;
        local function f_batch_write_play_elements_get_api_data(p31) --[[ Name: batch_write_play_elements_get_api_data ]] --[[ Line: 78 ]]
            local v32 = {}
            for v33 = 1, p31:count() do
                v32[v33] = p31:get(v33):get_api_data()
            end;
            return v32;
        end;
        local function f_batch_write_new_plays_list_with_callback_list(p_u_34, p_u_35) --[[ Name: batch_write_new_plays_list_with_callback_list ]] --[[ Line: 86 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_11 ]]
            if p_u_34:count() ~= 0 then
                local v_u_36 = p_u_34:get(1):get_songkey()
                v_u_5:spawn(function() --[[ Line: 90 ]]
                    --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_11, (copy 3): v_u_36, (copy 4): p_u_34, (copy 5): p_u_35 ]]
                    v_u_5:wait(v_u_5:rand_rangef(0.5, 1))
                    v_u_11:datastore_update_songkey_top_scores_from_new_plays_list_no_cooldown(v_u_36, p_u_34, function(p37) --[[ Line: 92 ]]
                        --[[ Upvalues: (ref 1): p_u_35 ]]
                        for _, v38 in p_u_35:key_itr() do
                            v38(p37)
                        end;
                    end)
                end)
                v_u_5:spawn(function() --[[ Line: 99 ]]
                    --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_11, (copy 3): v_u_36, (copy 4): p_u_34 ]]
                    v_u_5:wait(v_u_5:rand_rangef(1, 1.5))
                    v_u_11:datastore_update_songkey_recent_play_from_new_plays_list_no_cooldown(v_u_36, p_u_34)
                end)
            end;
        end;
        v_u_11.dsapi_player_song_stats_batch_write_play = function(p_u_39, p40, p41, p42, p_u_43) --[[ Name: dsapi_player_song_stats_batch_write_play ]] --[[ Line: 105 ]]
            --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_4, (copy 3): p_u_10, (copy 4): f_batch_write_play_elements_get_api_data, (ref 5): v_u_2, (ref 6): v_u_9, (ref 7): v_u_5, (copy 8): f_batch_write_new_plays_list_with_callback_list, (ref 9): s_HttpService_0 ]]
            local v_u_44 = v_u_6.Builder:new()
            local v_u_45 = ""
            local v_u_46 = nil
            if v_u_4.PlayerSongStatDoWebAPIWrite == true then
                v_u_44:begin()
                p_u_10._api:api_player_song_stats_batch_write_play(p40, p41, f_batch_write_play_elements_get_api_data(p42), function(p47, p48) --[[ Line: 117 ]]
                    --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_45, (ref 3): v_u_46, (copy 4): v_u_44 ]]
                    if v_u_4.PlayerSongStatDoWebAPIRead == true then
                        v_u_45 = p47
                        v_u_46 = p48
                    end;
                    v_u_44:finish()
                end)
            end;
            if v_u_4.PlayerSongStatDoDatastoreAPIWrite == true then
                local v_u_49 = v_u_6.Builder:new()
                local v_u_50 = v_u_2:new()
                local v_u_51 = v_u_2:new()
                local v_u_52 = v_u_2:new()
                v_u_2:for_each(p42, function(p53) --[[ Line: 133 ]]
                    --[[ Upvalues: (ref 1): v_u_9, (ref 2): v_u_6, (ref 3): v_u_5, (copy 4): p_u_39, (copy 5): v_u_51, (copy 6): v_u_52, (copy 7): v_u_49, (copy 8): v_u_50 ]]
                    local v_u_54 = p53:get_as_player_song_play()
                    local v_u_55 = v_u_9.WritePlayResult:new(v_u_54)
                    local v_u_56 = v_u_6.Builder:new()
                    v_u_56:begin()
                    v_u_5:spawn(function() --[[ Line: 139 ]]
                        --[[ Upvalues: (ref 1): v_u_5, (ref 2): p_u_39, (copy 3): v_u_54, (ref 4): v_u_9, (copy 5): v_u_55, (copy 6): v_u_56 ]]
                        v_u_5:wait(v_u_5:rand_rangef(0.1, 0.5))
                        p_u_39:datastore_get_player_song_stat_collection(v_u_54:get_rbxid(), function(p57) --[[ Line: 144 ]]
                            --[[ Upvalues: (ref 1): v_u_9, (ref 2): v_u_54, (ref 3): v_u_55, (ref 4): p_u_39, (ref 5): v_u_56 ]]
                            v_u_9:play_update_player_song_stat_collection(v_u_54, p57, v_u_55)
                            p_u_39:datastore_set_player_song_stat_collection(v_u_54:get_rbxid(), p57, function() --[[ Line: 153 ]]
                                --[[ Upvalues: (ref 1): v_u_56 ]]
                                v_u_56:finish()
                            end)
                        end)
                    end)
                    v_u_56:begin()
                    v_u_51:push_back(v_u_54)
                    v_u_52:push_back(function(p58) --[[ Line: 164 ]]
                        --[[ Upvalues: (copy 1): v_u_54, (copy 2): v_u_55, (copy 3): v_u_56 ]]
                        local v59 = 0
                        for v60, v61 in p58:key_itr() do
                            if v61:get_rbxid() == v_u_54:get_rbxid() then
                                v59 = v60
                                break;
                            end;
                        end;
                        v_u_55:set_rank(v59)
                        v_u_55:set_total_count(p58:count())
                        v_u_56:finish()
                    end)
                    v_u_5:spawn(function() --[[ Line: 177 ]]
                        --[[ Upvalues: (ref 1): v_u_5, (ref 2): p_u_39, (copy 3): v_u_54 ]]
                        v_u_5:wait(v_u_5:rand_rangef(1.5, 2))
                        p_u_39:datastore_update_player_recent_plays_no_cooldown(v_u_54:get_rbxid(), v_u_54)
                    end)
                    v_u_49:begin()
                    v_u_56:wait_for_finish(function() --[[ Line: 183 ]]
                        --[[ Upvalues: (ref 1): v_u_50, (copy 2): v_u_55, (ref 3): v_u_49 ]]
                        v_u_50:push_back(v_u_55:to_table())
                        v_u_49:finish()
                    end)
                end)
                f_batch_write_new_plays_list_with_callback_list(v_u_51, v_u_52)
                v_u_44:begin()
                v_u_49:wait_for_finish(function() --[[ Line: 192 ]]
                    --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_45, (ref 3): s_HttpService_0, (copy 4): v_u_50, (ref 5): v_u_46, (copy 6): v_u_44 ]]
                    if v_u_4.PlayerSongStatDoDatastoreAPIRead == true then
                        v_u_45 = s_HttpService_0:JSONEncode(v_u_50:get_table())
                        v_u_46 = v_u_50:get_table()
                    end;
                    v_u_44:finish()
                end)
            end;
            v_u_44:wait_for_finish(function() --[[ Line: 205 ]]
                --[[ Upvalues: (copy 1): p_u_43, (ref 2): v_u_45, (ref 3): v_u_46 ]]
                p_u_43(v_u_45, v_u_46)
            end)
        end;
        local v_u_62 = v_u_3:new()
        local function f_add_playerid_to_cached_player_song_stat_collection(p63, p64) --[[ Name: add_playerid_to_cached_player_song_stat_collection ]] --[[ Line: 211 ]]
            --[[ Upvalues: (copy 1): v_u_62, (ref 2): v_u_8 ]]
            if v_u_62:contains(p63) ~= true then
                v_u_62:add(p63, v_u_8:new())
            end;
            v_u_62:get(p63):load_from_json_obj(p64:to_json_obj())
        end;
        local v_u_65 = v_u_7:new():set_cooldown(0.25)
        local v_u_66 = v_u_7:new():set_cooldown(1)
        local v_u_67 = s_DataStoreService_0:GetDataStore("PlayerSongStatCollection")
        local function _(p68) --[[ Name: player_ds_key ]] --[[ Line: 225 ]]
            return string.format("player%d_pssc", p68);
        end;
        v_u_11.datastore_get_player_song_stat_collection = function(_, p_u_69, p_u_70) --[[ Name: datastore_get_player_song_stat_collection ]] --[[ Line: 227 ]]
            --[[ Upvalues: (copy 1): v_u_62, (ref 2): v_u_8, (copy 3): v_u_65, (copy 4): p_u_10, (copy 5): v_u_67, (copy 6): f_add_playerid_to_cached_player_song_stat_collection ]]
            if v_u_62:contains(p_u_69) == true then
                local v71 = v_u_8:new()
                v71:load_from_json_obj(v_u_62:get(p_u_69):to_json_obj())
                return p_u_70(v71);
            end;
            local v_u_72 = string.format("player%d_pssc", p_u_69)
            v_u_65:queue_key_request(p_u_69, function() --[[ Line: 235 ]]
                --[[ Upvalues: (ref 1): p_u_10, (ref 2): v_u_67, (copy 3): v_u_72, (ref 4): v_u_8, (ref 5): f_add_playerid_to_cached_player_song_stat_collection, (copy 6): p_u_69, (copy 7): p_u_70 ]]
                p_u_10._datastore_api:do_datastore_get(v_u_67, v_u_72, function(p73, p74) --[[ Line: 239 ]]
                    --[[ Upvalues: (ref 1): v_u_8, (ref 2): f_add_playerid_to_cached_player_song_stat_collection, (ref 3): p_u_69, (ref 4): p_u_70 ]]
                    local v75 = v_u_8:new()
                    if p73 and typeof(p74) == "table" then
                        v75:load_from_json_obj(p74)
                        f_add_playerid_to_cached_player_song_stat_collection(p_u_69, v75)
                    end;
                    p_u_70(v75)
                end)
            end)
        end;
        v_u_11.datastore_set_player_song_stat_collection = function(_, p_u_76, p_u_77, p_u_78) --[[ Name: datastore_set_player_song_stat_collection ]] --[[ Line: 251 ]]
            --[[ Upvalues: (copy 1): v_u_66, (copy 2): p_u_10, (copy 3): v_u_67, (copy 4): f_add_playerid_to_cached_player_song_stat_collection ]]
            local v_u_79 = string.format("player%d_pssc", p_u_76)
            v_u_66:queue_key_request(p_u_76, function() --[[ Line: 253 ]]
                --[[ Upvalues: (ref 1): p_u_10, (ref 2): v_u_67, (copy 3): v_u_79, (copy 4): p_u_77, (ref 5): f_add_playerid_to_cached_player_song_stat_collection, (copy 6): p_u_76, (copy 7): p_u_78 ]]
                p_u_10._datastore_api:do_datastore_set(v_u_67, v_u_79, p_u_77:to_json_obj(), function(_, _) --[[ Line: 258 ]]
                    --[[ Upvalues: (ref 1): f_add_playerid_to_cached_player_song_stat_collection, (ref 2): p_u_76, (ref 3): p_u_77, (ref 4): p_u_78 ]]
                    f_add_playerid_to_cached_player_song_stat_collection(p_u_76, p_u_77)
                    if p_u_78 then
                        p_u_78()
                    end;
                end)
            end)
        end;
        local v_u_80 = s_DataStoreService_0:GetDataStore("PlayerSongPlay")
        local function f_top_scores_ds_key(p81) --[[ Name: top_scores_ds_key ]] --[[ Line: 274 ]]
            return string.format("song%d_top", p81);
        end;
        local function f_recent_plays_ds_key(p82) --[[ Name: recent_plays_ds_key ]] --[[ Line: 275 ]]
            return string.format("song%d_recent", p82);
        end;
        local function f_player_recent_plays_ds_key(p83) --[[ Name: player_recent_plays_ds_key ]] --[[ Line: 276 ]]
            return string.format("player%d_recent", p83);
        end;
        local function f_datastore_update_player_song_play_list_from_new_plays_list(p_u_84, p85, p_u_86, p_u_87) --[[ Name: datastore_update_player_song_play_list_from_new_plays_list ]] --[[ Line: 278 ]]
            --[[ Upvalues: (ref 1): v_u_2, (copy 2): p_u_10, (copy 3): v_u_80, (ref 4): v_u_9 ]]
            local v_u_88 = v_u_2:new()
            p_u_10._datastore_api:do_datastore_update(v_u_80, p85(), function(p89) --[[ Line: 283 ]]
                --[[ Upvalues: (ref 1): v_u_88, (ref 2): v_u_2, (ref 3): v_u_9, (copy 4): p_u_84, (copy 5): p_u_86 ]]
                v_u_88 = v_u_2:new()
                if typeof(p89) == "table" then
                    v_u_88 = v_u_9:tab_to_list(p89)
                end;
                for _, v90 in p_u_84:key_itr() do
                    v_u_88:push_front(v90)
                end;
                p_u_86(v_u_88)
                v_u_9:keep_list_within_datastore_list_count(v_u_88)
                return v_u_9:list_to_tab(v_u_88);
            end, function() --[[ Line: 297 ]]
                --[[ Upvalues: (copy 1): p_u_87, (ref 2): v_u_88 ]]
                if p_u_87 then
                    p_u_87(v_u_88)
                end;
            end)
        end;
        v_u_11.datastore_update_songkey_top_scores_from_new_plays_list_no_cooldown = function(_, p_u_91, p92, p_u_93) --[[ Name: datastore_update_songkey_top_scores_from_new_plays_list_no_cooldown ]] --[[ Line: 303 ]]
            --[[ Upvalues: (copy 1): f_datastore_update_player_song_play_list_from_new_plays_list, (copy 2): f_top_scores_ds_key, (ref 3): v_u_3, (ref 4): v_u_2 ]]
            f_datastore_update_player_song_play_list_from_new_plays_list(p92, function() --[[ Line: 306 ]]
                --[[ Upvalues: (ref 1): f_top_scores_ds_key, (copy 2): p_u_91 ]]
                return f_top_scores_ds_key(p_u_91);
            end, function(p94) --[[ Line: 309 ]]
                --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_2 ]]
                local v95 = v_u_3:new()
                for _, v96 in p94:key_itr() do
                    if v95:contains(v96:get_rbxid()) == true then
                        if v96:get_score() > v95:get(v96:get_rbxid()):get_score() then
                            v95:add(v96:get_rbxid(), v96)
                        end;
                    else
                        v95:add(v96:get_rbxid(), v96)
                    end;
                end;
                p94:clear()
                for _, v97 in v95:key_itr() do
                    p94:push_back(v97)
                end;
                v_u_2:sort_fast(p94, function(p98, p99) --[[ Line: 327 ]]
                    if p98:get_score() == p99:get_score() then
                        return p98:get_time() < p99:get_time();
                    else
                        return p98:get_score() > p99:get_score();
                    end;
                end)
            end, function(p100) --[[ Line: 334 ]]
                --[[ Upvalues: (copy 1): p_u_93 ]]
                if p_u_93 then
                    p_u_93(p100)
                end;
            end)
        end;
        v_u_11.datastore_update_songkey_recent_play_from_new_plays_list_no_cooldown = function(_, p_u_101, p102, p_u_103) --[[ Name: datastore_update_songkey_recent_play_from_new_plays_list_no_cooldown ]] --[[ Line: 340 ]]
            --[[ Upvalues: (copy 1): f_datastore_update_player_song_play_list_from_new_plays_list, (copy 2): f_recent_plays_ds_key, (ref 3): v_u_2 ]]
            f_datastore_update_player_song_play_list_from_new_plays_list(p102, function() --[[ Line: 343 ]]
                --[[ Upvalues: (ref 1): f_recent_plays_ds_key, (copy 2): p_u_101 ]]
                return f_recent_plays_ds_key(p_u_101);
            end, function(p104) --[[ Line: 346 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                v_u_2:sort_fast(p104, function(p105, p106) --[[ Line: 347 ]]
                    if p105:get_time() == p106:get_time() then
                        return p105:get_rbxid() > p106:get_rbxid();
                    else
                        return p105:get_time() > p106:get_time();
                    end;
                end)
            end, function(p107) --[[ Line: 354 ]]
                --[[ Upvalues: (copy 1): p_u_103 ]]
                if p_u_103 then
                    p_u_103(p107)
                end;
            end)
        end;
        local v_u_108 = v_u_3:new()
        v_u_11.datastore_update_player_recent_plays_no_cooldown = function(p109, p_u_110, p_u_111, p_u_112) --[[ Name: datastore_update_player_recent_plays_no_cooldown ]] --[[ Line: 362 ]]
            --[[ Upvalues: (copy 1): v_u_108, (ref 2): v_u_1, (ref 3): v_u_9, (copy 4): p_u_10, (copy 5): v_u_80 ]]
            local function f_fn_on_cache_present_do_datastore_write() --[[ Name: fn_on_cache_present_do_datastore_write ]] --[[ Line: 364 ]]
                --[[ Upvalues: (ref 1): v_u_108, (copy 2): p_u_110, (ref 3): v_u_1, (copy 4): p_u_111, (ref 5): v_u_9, (ref 6): p_u_10, (ref 7): v_u_80, (copy 8): p_u_112 ]]
                if v_u_108:contains(p_u_110) ~= true then
                    return v_u_1:warnf("datastore_update_player_recent_plays_no_cooldown no cached recent plays for playerid(%d)", p_u_110);
                end;
                local v_u_113 = v_u_108:get(p_u_110)
                v_u_113:push_front(p_u_111)
                v_u_9:keep_list_within_datastore_list_count(v_u_113)
                p_u_10._datastore_api:do_datastore_set(v_u_80, string.format("player%d_recent", p_u_110), v_u_9:list_to_tab(v_u_113), function() --[[ Line: 376 ]]
                    --[[ Upvalues: (ref 1): p_u_112, (copy 2): v_u_113 ]]
                    if p_u_112 then
                        p_u_112(v_u_113)
                    end;
                end)
            end;
            if v_u_108:contains(p_u_110) == true then
                f_fn_on_cache_present_do_datastore_write()
            else
                p109:datastore_get_player_recent_plays_play_list_no_cooldown(p_u_110, function(p114) --[[ Line: 383 ]]
                    --[[ Upvalues: (ref 1): v_u_108, (copy 2): p_u_110, (copy 3): f_fn_on_cache_present_do_datastore_write ]]
                    v_u_108:add(p_u_110, p114)
                    f_fn_on_cache_present_do_datastore_write()
                end)
            end;
        end;
        local function _(p115, p_u_116) --[[ Name: datastore_get_player_song_play_list ]] --[[ Line: 392 ]]
            --[[ Upvalues: (copy 1): p_u_10, (copy 2): v_u_80, (ref 3): v_u_9 ]]
            p_u_10._datastore_api:do_datastore_get(v_u_80, p115(), function(_, p117) --[[ Line: 396 ]]
                --[[ Upvalues: (copy 1): p_u_116, (ref 2): v_u_9 ]]
                p_u_116(v_u_9:tab_to_list(p117))
            end)
        end;
        v_u_11.datastore_get_songkey_top_scores_play_list_no_cooldown = function(_, p_u_118, p_u_119) --[[ Name: datastore_get_songkey_top_scores_play_list_no_cooldown ]] --[[ Line: 402 ]]
            --[[ Upvalues: (copy 1): f_top_scores_ds_key, (copy 2): p_u_10, (copy 3): v_u_80, (ref 4): v_u_9 ]]
            local function v_u_121(p120) --[[ Line: 407 ]]
                --[[ Upvalues: (copy 1): p_u_119 ]]
                p_u_119(p120)
            end;
            p_u_10._datastore_api:do_datastore_get(v_u_80, (function() --[[ Line: 404 ]]
                --[[ Upvalues: (ref 1): f_top_scores_ds_key, (copy 2): p_u_118 ]]
                return f_top_scores_ds_key(p_u_118);
            end)(), function(_, p122) --[[ Line: 396 ]]
                --[[ Upvalues: (copy 1): v_u_121, (ref 2): v_u_9 ]]
                v_u_121(v_u_9:tab_to_list(p122))
            end)
        end;
        v_u_11.datastore_get_songkey_recent_plays_play_list_no_cooldown = function(_, p_u_123, p_u_124) --[[ Name: datastore_get_songkey_recent_plays_play_list_no_cooldown ]] --[[ Line: 413 ]]
            --[[ Upvalues: (copy 1): f_recent_plays_ds_key, (copy 2): p_u_10, (copy 3): v_u_80, (ref 4): v_u_9 ]]
            local function v_u_126(p125) --[[ Line: 418 ]]
                --[[ Upvalues: (copy 1): p_u_124 ]]
                p_u_124(p125)
            end;
            p_u_10._datastore_api:do_datastore_get(v_u_80, (function() --[[ Line: 415 ]]
                --[[ Upvalues: (ref 1): f_recent_plays_ds_key, (copy 2): p_u_123 ]]
                return f_recent_plays_ds_key(p_u_123);
            end)(), function(_, p127) --[[ Line: 396 ]]
                --[[ Upvalues: (copy 1): v_u_126, (ref 2): v_u_9 ]]
                v_u_126(v_u_9:tab_to_list(p127))
            end)
        end;
        v_u_11.datastore_get_player_recent_plays_play_list_no_cooldown = function(_, p_u_128, p_u_129) --[[ Name: datastore_get_player_recent_plays_play_list_no_cooldown ]] --[[ Line: 424 ]]
            --[[ Upvalues: (copy 1): f_player_recent_plays_ds_key, (copy 2): p_u_10, (copy 3): v_u_80, (ref 4): v_u_9 ]]
            local function v_u_131(p130) --[[ Line: 429 ]]
                --[[ Upvalues: (copy 1): p_u_129 ]]
                p_u_129(p130)
            end;
            p_u_10._datastore_api:do_datastore_get(v_u_80, (function() --[[ Line: 426 ]]
                --[[ Upvalues: (ref 1): f_player_recent_plays_ds_key, (copy 2): p_u_128 ]]
                return f_player_recent_plays_ds_key(p_u_128);
            end)(), function(_, p132) --[[ Line: 396 ]]
                --[[ Upvalues: (copy 1): v_u_131, (ref 2): v_u_9 ]]
                v_u_131(v_u_9:tab_to_list(p132))
            end)
        end;
        v_u_11.player_disconnecting = function(_, p133) --[[ Name: player_disconnecting ]] --[[ Line: 435 ]]
            --[[ Upvalues: (copy 1): v_u_108, (copy 2): v_u_62 ]]
            v_u_108:remove(p133)
            v_u_62:remove(p133)
        end;
        return v_u_11;
    end
};
