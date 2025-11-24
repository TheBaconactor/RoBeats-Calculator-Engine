-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:21 PM
-- Time elapsed: 17 milliseconds

require(game.ReplicatedStorage.Server.ServerGameInstance_Elements.ServerGameInstanceMode)
local v_u_1 = require(game.ReplicatedStorage.Shared.AudioRank)
require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_2 = require(game.ReplicatedStorage.Server.DebugOut)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_6 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_7 = require(game.ReplicatedStorage.Server.ServerPlayerSongStatsManager)
local v_u_8 = require(game.ReplicatedStorage.Avatar.PlayerBlobAvatar)
local v_u_9 = require(game.ReplicatedStorage.Shared.Constants)
local v_u_10 = require(game.ReplicatedStorage.PlayerInfo.VIPInfo)
local v_u_11 = require(game.ReplicatedStorage.Avatar.GearStats)
require(game.ReplicatedStorage.PlayerInfo.SpecialEventInfo)
require(game.ReplicatedStorage.Shared.AssertType)
local v_u_12 = require(game.ReplicatedStorage.PlayerInfo.MatchEndRouletteReward)
require(game.ReplicatedStorage.Crafting.CraftDatabase)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_13 = require(game.ReplicatedStorage.Shared.MatchMode)
local v_u_14 = require(game.ReplicatedStorage.Pets.PetUtils)
require(game.ReplicatedStorage.Shared.GuildData)
local v_u_15 = require(game.ReplicatedStorage.Shared.GuildBonusUtil)
local v16 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_17 = nil
v16:require_server(function() --[[ Line: 28 ]]
    --[[ Upvalues: (ref 1): v_u_17 ]]
    v_u_17 = require(game.ReplicatedStorage.Server.ServerSpecialEventManager)
end)
return {
    ["new"] = function(_, p_u_18, p_u_19) --[[ Name: new ]] --[[ Line: 34 ]]
        --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_8, (copy 3): v_u_11, (copy 4): v_u_13, (copy 5): v_u_2, (copy 6): v_u_5, (copy 7): v_u_1, (copy 8): v_u_7, (copy 9): v_u_10, (copy 10): v_u_9, (copy 11): v_u_12, (copy 12): v_u_15, (copy 13): v_u_14, (copy 14): v_u_6, (ref 15): v_u_17, (copy 16): v_u_4 ]]
        local v20 = {
            ["update"] = function(_, _) end
        }
        v20.game_has_ended = function(p21) --[[ Name: game_has_ended ]] --[[ Line: 37 ]]
            --[[ Upvalues: (copy 1): p_u_19, (ref 2): v_u_3, (copy 3): p_u_18, (ref 4): v_u_8, (ref 5): v_u_11, (ref 6): v_u_13, (ref 7): v_u_2, (ref 8): v_u_5, (ref 9): v_u_1, (ref 10): v_u_7, (ref 11): v_u_10, (ref 12): v_u_9, (ref 13): v_u_12, (ref 14): v_u_15, (ref 15): v_u_14, (ref 16): v_u_6, (ref 17): v_u_17 ]]
            local l__selected_song_key_0 = p_u_19._selected_song_key
            local v_u_22 = v_u_3:new()
            p_u_19._util:slots_foreach(function(p_u_23, p24) --[[ Line: 42 ]]
                --[[ Upvalues: (ref 1): p_u_18, (copy 2): l__selected_song_key_0, (ref 3): v_u_8, (ref 4): v_u_11, (ref 5): p_u_19, (ref 6): v_u_13, (ref 7): v_u_2, (ref 8): v_u_5, (ref 9): v_u_1, (ref 10): v_u_7, (copy 11): v_u_22 ]]
                p_u_18._game_instance_manager:get_reward_cooldown_manager():track_userid_last_played_song(p_u_23._id, l__selected_song_key_0)
                local v25 = 0
                local v26 = 0
                local v27 = 0
                local v28 = p_u_18._player_blob_manager:get_cached_blob(p_u_23._id)
                p_u_23._score = 0
                local v29, v30
                if v28 then
                    v29 = v_u_8:get_playerblob_base_gearpower_v2(v28, p_u_18._api:get_day_id(), p_u_18._api:get_week_id()) + v_u_8:get_playerblob_songkey_color_gearpower_v2(v28, l__selected_song_key_0, p_u_18._api:get_day_id(), p_u_18._api:get_week_id())
                    v30 = v_u_8:get_playerblob_statsdict(v28, p_u_18._api:get_day_id(), p_u_18._api:get_week_id())[v_u_11.Type.PerfectTime]
                    if v30 == nil then
                        v30 = v25
                    end;
                    if p_u_19._player_note_sequence_info:contains(p24) then
                        local v31 = p_u_19._player_note_sequence_info:get(p24)
                        v26, v27 = v31:get_hit_time_avg_ct()
                        p_u_23._score = v31:get_player_score():get_score()
                        if p_u_23._match_mode == v_u_13.Casual then
                            local v32, v33, v34, v35 = v31:get_player_naked_score():get_stat_counts()
                            p_u_23._perfect_count = v32
                            p_u_23._great_count = v33
                            p_u_23._okay_count = v34
                            p_u_23._miss_count = v35
                        else
                            local v36, v37, v38, v39 = v31:get_player_score():get_stat_counts()
                            p_u_23._perfect_count = v36
                            p_u_23._great_count = v37
                            p_u_23._okay_count = v38
                            p_u_23._miss_count = v39
                        end;
                        if p_u_23._accuracy > v31:get_player_score():get_accuracy() then
                            v_u_2:warnf("accuracy mismatch: playeracc(%.4f) serveracc(%.4f)", p_u_23._accuracy, v31:get_player_score():get_accuracy())
                            v_u_2:warnf(v31:get_player_score():to_string())
                        end;
                        p_u_23._accuracy = v31:get_player_score():get_accuracy()
                        if v_u_5:is_dev_build() then
                            v_u_2:puts("GameEnded PlayerScore")
                            v_u_2:puts("\t" .. v31:get_player_score():to_string())
                        end;
                        p_u_23._naked_score = v31:get_player_naked_score():get_score()
                    end;
                else
                    v30 = v25
                    v29 = 0
                end;
                local v40 = p_u_18._player_manager:id_to_player(p_u_23._id)
                if v40 == nil then
                    return;
                elseif p_u_23._score <= 0 then
                    return;
                elseif not p_u_23:did_early_quit_or_leave() then
                    local v41 = v_u_1:accuracy_to_rank_value(p_u_23._accuracy)
                    local v42 = {
                        ["rbxid"] = p_u_23._id,
                        ["score"] = p_u_23._score,
                        ["accuracy"] = p_u_23._accuracy,
                        ["naked_score"] = p_u_23._naked_score,
                        ["rank"] = v41,
                        ["perfect_count"] = p_u_23._perfect_count,
                        ["great_count"] = p_u_23._great_count,
                        ["okay_count"] = p_u_23._okay_count,
                        ["miss_count"] = p_u_23._miss_count,
                        ["fever_percentage"] = p_u_23._fever_percentage,
                        ["gear_power"] = v29,
                        ["perfect_time"] = v30,
                        ["avg_ms_delta"] = v26,
                        ["avg_ms_delta_ct"] = v27
                    }
                    p_u_18._leaderboard_manager:write_play_for_playerid_and_songkey(p_u_23._id, l__selected_song_key_0, p_u_23, v42)
                    local v46 = v_u_7.BatchWritePlayElement:new(v40, l__selected_song_key_0, p_u_23._score, v41, p_u_23._accuracy, p_u_23._naked_score, v29, v42, p_u_23._gear_stats, function(p43) --[[ Line: 152 ]]
                        --[[ Upvalues: (copy 1): p_u_23, (ref 2): v_u_5, (ref 3): p_u_18, (ref 4): p_u_19 ]]
                        if p43.IsNewBestScore == true then
                            local v44
                            if p43.Rank > 0 then
                                v44 = string.format("New personal best for %s, score: %s! Ranked %s.", p_u_23._name, v_u_5:comma_value(p43.BestScore), v_u_5:num_placify(p43.Rank))
                            else
                                v44 = string.format("New personal best for %s, score: %s!", p_u_23._name, v_u_5:comma_value(p43.BestScore))
                            end;
                            p_u_18._chat:gameid_send_system_message(p_u_19._game_id, v44, function(p45) --[[ Line: 174 ]]
                                --[[ Upvalues: (ref 1): v_u_5 ]]
                                p45:set_channel_name("")
                                p45:set_icon(v_u_5:get_song_icon())
                            end)
                        end;
                    end)
                    v46:set_match_mode(p_u_23._match_mode)
                    v_u_22:push_back(v46)
                end;
            end)
            local v47 = p21:get_players_score_sorted()
            local v48 = p21:get_id_to_naked_place()
            local v_u_49 = v47:count()
            local function _() --[[ Name: decrement_players_to_sync ]] --[[ Line: 190 ]]
                --[[ Upvalues: (ref 1): v_u_49, (ref 2): p_u_18, (copy 3): l__selected_song_key_0, (ref 4): p_u_19, (copy 5): v_u_22 ]]
                local v50 = v_u_49
                v_u_49 = v50 - 1
                if v50 > 0 and v_u_49 <= 0 then
                    p_u_18._player_song_stats_manager:batch_write_play(l__selected_song_key_0, p_u_19._num_leavers, v_u_22)
                end;
            end;
            local v_u_51 = v47:count()
            local v_u_52 = 0
            p_u_19._util:slots_foreach(function(p53, _) --[[ Line: 202 ]]
                --[[ Upvalues: (ref 1): v_u_52 ]]
                v_u_52 = v_u_52 + p53._score
            end)
            local v_u_54 = v_u_49
            local v55 = v_u_52
            for v56 = 1, v47:count() do
                local v_u_57 = v47:get(v56)
                local l__accuracy_0 = v_u_57._accuracy
                local v_u_58
                if v_u_57._match_mode == v_u_13.Casual and v48:contains(v_u_57._id) then
                    v_u_58 = v48:get(v_u_57._id)
                else
                    v_u_58 = v56
                end;
                local v_u_59 = p21:get_match_coin_reward(v_u_58, v_u_51, l__accuracy_0)
                local v_u_60 = p_u_18._player_blob_manager:get_cached_blob(v_u_57._id)
                local v_u_61 = (v_u_60 == nil or not v_u_10:playerblob_has_vip_for_current_day(v_u_60, p_u_18._api:get_day_id())) and 0 or v_u_59
                local l__like_count_0 = v_u_57._like_count
                local v_u_62 = l__like_count_0 * v_u_9.SPECTATE_CHEER_COIN_AMOUNT
                local v63 = v_u_59 + v_u_61 + 0 + 0 + v_u_62
                local v_u_64 = p_u_18._player_manager:id_to_player(v_u_57._id)
                if v_u_64 == nil then
                    v_u_49 = v_u_54 - 1
                    if v_u_54 > 0 and v_u_49 <= 0 then
                        p_u_18._player_song_stats_manager:batch_write_play(l__selected_song_key_0, p_u_19._num_leavers, v_u_22)
                    end;
                    v_u_2:warnf("ServerGameInstance_GameEnded:game_has_ended() cannot find player of id(%s)", (tostring(v_u_57._id)))
                    v_u_54 = v_u_49
                elseif v_u_57:did_early_quit_or_leave() then
                    v_u_49 = v_u_54 - 1
                    if v_u_54 > 0 and v_u_49 <= 0 then
                        p_u_18._player_song_stats_manager:batch_write_play(l__selected_song_key_0, p_u_19._num_leavers, v_u_22)
                        v_u_54 = v_u_49
                    else
                        v_u_54 = v_u_49
                    end;
                else
                    local v65 = v_u_3:new()
                    local v_u_66 = p_u_18._special_event_manager:write_special_event_data_for_play(p_u_19, l__selected_song_key_0, v_u_58, v_u_51, v_u_57, v65)
                    local v67 = p_u_18._game_instance_manager:get_reward_cooldown_manager():get_play_count_for_userid(v_u_64.UserId)
                    p_u_18._game_instance_manager:get_reward_cooldown_manager():add_play_for_userid(v_u_64.UserId)
                    local v_u_68 = v_u_12:get_reward_list_for_match(l__selected_song_key_0, v_u_51, l__accuracy_0, v_u_60, v67)
                    local v_u_69
                    if v_u_68:count() > 0 then
                        v_u_69 = v_u_12:reward_list_roll(v_u_68)
                        if v_u_15:playerblob_is_bonus_id_active_for_weekid(v_u_60, v_u_15.BonusType.DoubleRouletteRewards, p_u_18._api:get_week_id()) then
                            v_u_69:set_reward_count(v_u_69:get_reward_count() * 2)
                        end;
                        if v_u_69 then
                            v65:push_back(function(p70) --[[ Line: 261 ]]
                                --[[ Upvalues: (ref 1): v_u_69 ]]
                                v_u_69:apply_to_playerblob(p70)
                            end)
                        end;
                    else
                        v_u_69 = nil
                    end;
                    if v_u_9.MIN_ACCURACY_FOR_REWARDS_PCT <= l__accuracy_0 then
                        local v71 = v_u_14:get_play_exp_amount(l__selected_song_key_0, v_u_51, l__accuracy_0)
                        v71 = v71
                        local v72, v_u_73
                        if v_u_15:playerblob_is_bonus_id_active_for_weekid(v_u_60, v_u_15.BonusType.MorePetEXP, p_u_18._api:get_week_id()) then
                            v72 = v71 * 1
                            v_u_73 = v71 + v72
                        else
                            v_u_73 = v71
                            v72 = 0
                        end;
                        local v74
                        if v_u_10:playerblob_has_vip_for_current_day(v_u_60, p_u_18._api:get_day_id()) == true then
                            v74 = math.ceil(v71 * 0.1)
                            v_u_73 = v_u_73 + v74
                        else
                            v74 = 0
                        end;
                        local v_u_75 = v_u_14:playerblob_get_slot_to_owned_pet_dict(v_u_60)
                        if v_u_75:count() > 0 then
                            v65:push_back(function(_) --[[ Line: 285 ]]
                                --[[ Upvalues: (ref 1): v_u_75, (ref 2): v_u_14, (copy 3): v_u_60, (ref 4): v_u_73 ]]
                                v_u_75 = v_u_14:playerblob_get_slot_to_owned_pet_dict(v_u_60)
                                for _, v76 in v_u_75:key_itr() do
                                    v_u_14:ownedpet_apply_exp_gain(v76, v_u_73)
                                end;
                            end)
                            local v77 = p_u_18._chat:get_chat_service()
                            local v78 = p_u_18._chat:gameid_get_channel(p_u_19._game_id)
                            if v77 and v78 then
                                local v79 = ""
                                if v72 > 0 then
                                    v79 = v79 .. string.format(" (+%d Team Bonus)", v72)
                                end;
                                if v74 > 0 then
                                    v79 = v79 .. string.format(" (+%d VIP Bonus)", v74)
                                end;
                                v77:send_system_message_to_player_for_channel(v_u_64, v78, string.format("Your Mini(s) have gained %s EXP.%s", tostring(v_u_73), v79), function(p80) --[[ Line: 311 ]]
                                    --[[ Upvalues: (ref 1): v_u_14 ]]
                                    p80:set_channel_name("")
                                    p80:set_icon(v_u_14:get_pet_icon())
                                end)
                            end;
                        end;
                    end;
                    p_u_18._mission_manager:match_end_update_playerblob(v_u_64, {
                        ["SongKey"] = l__selected_song_key_0,
                        ["CoinRewardTotal"] = v63,
                        ["Place"] = v_u_58,
                        ["PlayerCount"] = v_u_51,
                        ["Score"] = v_u_57._score,
                        ["Accuracy"] = v_u_57._accuracy,
                        ["Misses"] = v_u_57._miss_count,
                        ["TotalScore"] = v55,
                        ["PlayerBlobUpdateCallbacks"] = v65,
                        ["GameInstance"] = p_u_19
                    }, function(p81) --[[ Line: 335 ]]
                        --[[ Upvalues: (copy 1): v_u_68, (ref 2): v_u_12, (ref 3): v_u_69, (ref 4): p_u_18, (ref 5): v_u_6, (copy 6): v_u_64, (copy 7): v_u_59, (ref 8): v_u_61, (ref 9): v_u_58, (copy 10): v_u_51, (copy 11): l__like_count_0, (copy 12): v_u_62, (copy 13): v_u_66, (copy 14): v_u_57, (ref 15): v_u_17, (ref 16): v_u_54, (copy 17): l__selected_song_key_0, (ref 18): p_u_19, (copy 19): v_u_22 ]]
                        local v_u_82 = nil
                        local v_u_83
                        if v_u_68 then
                            v_u_83 = v_u_12:reward_list_to_table(v_u_68)
                        else
                            v_u_83 = nil
                        end;
                        if v_u_69 then
                            v_u_82 = v_u_69:to_table()
                        end;
                        local function f_response() --[[ Name: response ]] --[[ Line: 345 ]]
                            --[[ Upvalues: (ref 1): p_u_18, (ref 2): v_u_6, (ref 3): v_u_64, (ref 4): v_u_59, (ref 5): v_u_61, (ref 6): v_u_58, (ref 7): v_u_51, (ref 8): l__like_count_0, (ref 9): v_u_62, (ref 10): v_u_66, (ref 11): v_u_83, (ref 12): v_u_82, (ref 13): v_u_57 ]]
                            p_u_18._evt:fire_event_to_client(v_u_6.EVT_Game_ServerNotifyMatchEndRewards, v_u_64, {
                                ["MatchCoinReward"] = v_u_59,
                                ["VIPCoinBonusReward"] = v_u_61,
                                ["NoMissReward"] = 0,
                                ["MostAccurateReward"] = 0,
                                ["Place"] = v_u_58,
                                ["PlayerCount"] = v_u_51,
                                ["SpectateCheerCount"] = l__like_count_0,
                                ["SpectateCheerCoins"] = v_u_62,
                                ["SpecialEventData"] = v_u_66,
                                ["RouletteTable"] = v_u_83,
                                ["RouletteReward"] = v_u_82,
                                ["DebugPlayerInfo"] = v_u_57:get_player_info(-1)
                            })
                        end;
                        local v84 = v_u_17.EventBase:event_play_table_get_fn_post_sync(v_u_66)
                        if v84 then
                            v84(p81, function() --[[ Line: 369 ]]
                                --[[ Upvalues: (copy 1): f_response ]]
                                f_response()
                            end)
                        else
                            f_response()
                        end;
                        local v85 = v_u_54
                        v_u_54 = v85 - 1
                        if v85 > 0 and v_u_54 <= 0 then
                            p_u_18._player_song_stats_manager:batch_write_play(l__selected_song_key_0, p_u_19._num_leavers, v_u_22)
                        end;
                    end)
                end;
            end;
            p_u_18._player_status_manager:send_match_end_event(p_u_19)
            p_u_18._mission_manager:on_game_instance_ended(p_u_19)
        end;
        v20.get_match_coin_reward = function(_, p86, p87, p88) --[[ Name: get_match_coin_reward ]] --[[ Line: 397 ]]
            --[[ Upvalues: (ref 1): v_u_9 ]]
            local v89 = 0
            if p88 < v_u_9.MIN_ACCURACY_FOR_REWARDS_PCT then
                return 0;
            end;
            local v90
            if p87 == 4 then
                v90 = ({
                    40,
                    35,
                    30,
                    25
                })[p86]
            elseif p87 == 3 then
                v90 = ({ 30, 25, 20 })[p86]
            elseif p87 == 2 then
                v90 = ({ 15, 10 })[p86]
            else
                v90 = p87 == 1 and 5 or v89
            end;
            return v90 == nil and 0 or v90;
        end;
        v20.get_players_score_sorted = function(_) --[[ Name: get_players_score_sorted ]] --[[ Line: 421 ]]
            --[[ Upvalues: (ref 1): v_u_3, (copy 2): p_u_19 ]]
            local v_u_91 = v_u_3:new()
            p_u_19._util:slots_foreach(function(p92, _) --[[ Line: 423 ]]
                --[[ Upvalues: (copy 1): v_u_91 ]]
                v_u_91:push_back(p92)
            end)
            v_u_91:sort(function(p93, p94) --[[ Line: 426 ]]
                return p93._score - p94._score;
            end)
            return v_u_91;
        end;
        v20.get_id_to_geared_place = function(p95) --[[ Name: get_id_to_geared_place ]] --[[ Line: 432 ]]
            --[[ Upvalues: (ref 1): v_u_4 ]]
            local v96 = p95:get_players_score_sorted()
            local v97 = v_u_4:new()
            for v98, v99 in v96:key_itr() do
                v97:add(v99._id, v98)
            end;
            return v97;
        end;
        v20.get_id_to_naked_place = function(_) --[[ Name: get_id_to_naked_place ]] --[[ Line: 441 ]]
            --[[ Upvalues: (ref 1): v_u_3, (copy 2): p_u_19, (ref 3): v_u_4 ]]
            local v_u_100 = v_u_3:new()
            p_u_19._util:slots_foreach(function(p101, _) --[[ Line: 443 ]]
                --[[ Upvalues: (copy 1): v_u_100 ]]
                v_u_100:push_back(p101)
            end)
            v_u_100:sort(function(p102, p103) --[[ Line: 446 ]]
                return p102._naked_score - p103._naked_score;
            end)
            local v104 = v_u_4:new()
            for v105 = 1, v_u_100:count() do
                v104:add(v_u_100:get(v105)._id, v105)
            end;
            return v104;
        end;
        v20.get_players_accuracy_sorted = function(_) --[[ Name: get_players_accuracy_sorted ]] --[[ Line: 457 ]]
            --[[ Upvalues: (ref 1): v_u_3, (copy 2): p_u_19 ]]
            local v_u_106 = v_u_3:new()
            p_u_19._util:slots_foreach(function(p107, _) --[[ Line: 459 ]]
                --[[ Upvalues: (copy 1): v_u_106 ]]
                v_u_106:push_back(p107)
            end)
            v_u_106:sort(function(p108, p109) --[[ Line: 462 ]]
                return p108._accuracy - p109._accuracy;
            end)
            return v_u_106;
        end;
        v20.notify_leave_ended_game = function(_, p110) --[[ Name: notify_leave_ended_game ]] --[[ Line: 468 ]]
            --[[ Upvalues: (copy 1): p_u_19 ]]
            p_u_19._util:mark_player_as_left(p110)
        end;
        return v20;
    end
};
