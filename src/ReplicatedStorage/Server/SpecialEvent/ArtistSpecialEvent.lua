-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:19 PM
-- Cached decompilation

require(game.ReplicatedStorage.PlayerInfo.SpecialEventInfo)
local v_u_1 = require(game.ReplicatedStorage.Shared.AssertType)
require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_4 = require(game.ReplicatedStorage.PlayerInfo.ArtistEventInfo)
local v_u_5 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_6 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_7 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_8 = require(game.ReplicatedStorage.PlayerInfo.VIPInfo)
require(game.ReplicatedStorage.Crafting.PlayerBlobCrafting)
local v_u_9 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_10 = require(game.ReplicatedStorage.Avatar.PlayerBlobAvatar)
local v_u_11 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_12 = require(game.ServerScriptService.ServerPromoCodes)
local v_u_13 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_14 = require(game.ReplicatedStorage.Shared.Constants)
require(game.ReplicatedStorage.Pets.PetDatabase)
require(game.ReplicatedStorage.Pets.PetUtils)
require(game.ReplicatedStorage.Shared.GuildData)
local v_u_15 = require(game.ReplicatedStorage.Shared.GuildBonusUtil)
local v_u_16 = require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
local v_u_17 = require(game.ReplicatedStorage.Server.SpecialEvent.ServerEventLeaderboardManager)
local v_u_18 = require(game.ReplicatedStorage.Server.SpecialEvent.ServerPetAssignmentManager)
local v19 = {}
local v20 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_21 = nil
v20:require_server(function() --[[ Line: 31 ]]
    --[[ Upvalues: (ref 1): v_u_21 ]]
    v_u_21 = require(game.ReplicatedStorage.Server.ServerSpecialEventManager)
end)
local v_u_22 = v_u_4:get_cheer_event_point_count()
v19.new = function(_, p_u_23) --[[ Name: new ]] --[[ Line: 37 ]]
    --[[ Upvalues: (ref 1): v_u_21, (copy 2): v_u_17, (copy 3): v_u_18, (copy 4): v_u_13, (copy 5): v_u_7, (copy 6): v_u_4, (copy 7): v_u_5, (copy 8): v_u_11, (copy 9): v_u_1, (copy 10): v_u_16, (copy 11): v_u_12, (copy 12): v_u_10, (copy 13): v_u_3, (copy 14): v_u_14, (copy 15): v_u_9, (copy 16): v_u_6, (copy 17): v_u_2, (copy 18): v_u_15, (copy 19): v_u_8, (copy 20): v_u_22 ]]
    local v24 = v_u_21.EventBase:new()
    local v_u_25 = v_u_17:new(p_u_23)
    local v_u_26 = v_u_18:new(p_u_23)
    local v_u_27 = v_u_13:new()
    local v_u_28 = v_u_13:new()
    local function f_cons() --[[ Name: cons ]] --[[ Line: 46 ]]
        --[[ Upvalues: (copy 1): v_u_25, (copy 2): v_u_26, (copy 3): p_u_23, (ref 4): v_u_7, (ref 5): v_u_4, (ref 6): v_u_5, (ref 7): v_u_13, (ref 8): v_u_11, (ref 9): v_u_1, (ref 10): v_u_16, (copy 11): v_u_27, (copy 12): v_u_28, (ref 13): v_u_12, (ref 14): v_u_10, (ref 15): v_u_3 ]]
        v_u_25:start()
        v_u_26:start()
        p_u_23._evt:wait_on_event(v_u_7.EVT_ArtistEvent_ValidatePlayer_Client, function(p_u_29) --[[ Line: 50 ]]
            --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_7, (ref 3): v_u_4, (ref 4): v_u_5 ]]
            local function _(p30, p31) --[[ Name: response ]] --[[ Line: 51 ]]
                --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_7, (copy 3): p_u_29 ]]
                p_u_23._evt:fire_event_to_client(v_u_7.EVT_ArtistEvent_ValidatePlayer_Server, p_u_29, p30, p31)
            end;
            p_u_23._player_blob_manager:get_verified_cached_blob(p_u_29.UserId, function(p32) --[[ Line: 54 ]]
                --[[ Upvalues: (ref 1): v_u_4, (ref 2): p_u_23, (copy 3): p_u_29, (ref 4): v_u_5, (ref 5): v_u_7 ]]
                local v33, v34 = v_u_4:is_event_active(p_u_23._api:get_day_event_list())
                if v33 and v_u_4:playerblob_needs_event_info_validate(p32, v34) then
                    v_u_4:playerblob_validate_event_info(p32, v34)
                    p_u_23._player_blob_manager:enqueue_blob_sync_request(p_u_29.UserId, v_u_5.PlayerBlobRequestType.Write, function(_) --[[ Line: 61 ]]
                        --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_7, (ref 3): p_u_29 ]]
                        p_u_23._evt:fire_event_to_client(v_u_7.EVT_ArtistEvent_ValidatePlayer_Server, p_u_29, true, "")
                    end)
                else
                    p_u_23._evt:fire_event_to_client(v_u_7.EVT_ArtistEvent_ValidatePlayer_Server, p_u_29, true, "")
                end;
            end)
        end)
        local v_u_35 = v_u_13:new()
        p_u_23._evt:wait_on_event(v_u_7.EVT_ArtistEvent_SendPromo_Client, function(p_u_36, p37) --[[ Line: 72 ]]
            --[[ Upvalues: (ref 1): v_u_11, (ref 2): v_u_1, (ref 3): v_u_16, (ref 4): v_u_27, (ref 5): p_u_23, (ref 6): v_u_7, (ref 7): v_u_13, (ref 8): v_u_28, (ref 9): v_u_12, (copy 10): v_u_35, (ref 11): v_u_5 ]]
            if v_u_11.PromoCodesActive == true then
                v_u_1:is_string(p37)
                local v38 = string.lower(p37)
                local l_UserId_0 = p_u_36.UserId
                local function f_response(p39, p40, p41) --[[ Name: response ]] --[[ Line: 78 ]]
                    --[[ Upvalues: (ref 1): v_u_16, (ref 2): v_u_27, (copy 3): l_UserId_0, (ref 4): p_u_23, (ref 5): v_u_7, (copy 6): p_u_36 ]]
                    local v42 = p41 == nil and {} or v_u_16.RewardInfo:list_to_table(p41)
                    v_u_27:remove(l_UserId_0)
                    p_u_23._evt:fire_event_to_client(v_u_7.EVT_ArtistEvent_SendPromo_ServerResponse, p_u_36, p39, p40, v42)
                end;
                if v_u_27:contains(l_UserId_0) then
                    return f_response(false, "Failed(active)");
                else
                    v_u_27:add_set(l_UserId_0)
                    if v_u_13:counter_get(v_u_28, l_UserId_0) > 20 then
                        return f_response(false, "Code not valid");
                    else
                        local v_u_43 = string.format("%s_%d", v38, p_u_36.UserId)
                        local v44, v_u_45 = v_u_12:singleton():find_promo(v38)
                        if v44 == true and v_u_45 ~= nil then
                            p_u_23._datastore_api:datastore_api_playerid_can_claim_promo_code(p_u_36.UserId, v_u_45, function(p46, p47, p_u_48) --[[ Line: 97 ]]
                                --[[ Upvalues: (ref 1): p_u_23, (copy 2): p_u_36, (ref 3): v_u_35, (copy 4): v_u_43, (copy 5): f_response, (ref 6): v_u_12, (copy 7): v_u_45, (ref 8): v_u_5, (ref 9): v_u_16 ]]
                                if p46 then
                                    p_u_23._player_blob_manager:get_verified_cached_blob(p_u_36.UserId, function(p49) --[[ Line: 99 ]]
                                        --[[ Upvalues: (ref 1): v_u_35, (ref 2): v_u_43, (ref 3): f_response, (ref 4): v_u_12, (ref 5): p_u_23, (ref 6): v_u_45, (ref 7): p_u_36, (ref 8): v_u_5, (copy 9): p_u_48, (ref 10): v_u_16 ]]
                                        if v_u_35:contains(v_u_43) then
                                            return f_response(false, "Already claimed hash");
                                        end;
                                        v_u_35:add_set(v_u_43)
                                        local v_u_50 = v_u_12:claim_rewards(p_u_23, p49, v_u_45)
                                        p_u_23._player_blob_manager:enqueue_blob_sync_request(p_u_36.UserId, v_u_5.PlayerBlobRequestType.Write, function(p51) --[[ Line: 107 ]]
                                            --[[ Upvalues: (ref 1): v_u_45, (copy 2): v_u_50, (ref 3): f_response, (ref 4): p_u_48, (ref 5): p_u_23, (ref 6): p_u_36, (ref 7): v_u_5, (ref 8): v_u_16 ]]
                                            local v_u_52 = v_u_45:get_description()
                                            if v_u_50.Message ~= nil then
                                                v_u_52 = v_u_50.Message
                                            end;
                                            local function f_on_finish(p53, p54) --[[ Name: on_finish ]] --[[ Line: 113 ]]
                                                --[[ Upvalues: (ref 1): f_response, (ref 2): v_u_52, (ref 3): p_u_48, (ref 4): v_u_50, (ref 5): p_u_23, (ref 6): p_u_36 ]]
                                                f_response(true, string.format("%s\nClaim number: %d.", v_u_52, p_u_48), p54)
                                                if v_u_50.PushPlayerInfoUpdated == true then
                                                    p_u_23._lobby_manager:push_player_info_updated(p_u_36.UserId)
                                                end;
                                                if v_u_50.UpdateEquippedData == true then
                                                    p_u_23._lobby_manager:update_player_character_to_equipped_data(p_u_36, p53)
                                                end;
                                            end;
                                            if v_u_50.FnPostSync == nil then
                                                f_on_finish(p51, v_u_16:reward_params_get_resolved_reward_list(v_u_50))
                                            else
                                                v_u_50.FnPostSync(p51)
                                                p_u_23._player_blob_manager:enqueue_blob_sync_request(p_u_36.UserId, v_u_5.PlayerBlobRequestType.Write, function(p55) --[[ Line: 128 ]]
                                                    --[[ Upvalues: (copy 1): f_on_finish, (ref 2): v_u_16, (ref 3): v_u_50 ]]
                                                    f_on_finish(p55, v_u_16:reward_params_get_resolved_reward_list(v_u_50))
                                                end)
                                            end;
                                        end)
                                    end)
                                else
                                    f_response(false, p47)
                                end;
                            end)
                        else
                            v_u_13:counter_increment(v_u_28, l_UserId_0)
                            f_response(false, "Code not valid.")
                        end;
                    end;
                end;
            else
                return;
            end;
        end)
        p_u_23._evt:wait_on_event(v_u_7.EVT_ArtistEvent_ShopPurchase_Client, function(p_u_56, p_u_57, p_u_58) --[[ Line: 148 ]]
            --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_7, (ref 3): v_u_4, (ref 4): v_u_10, (ref 5): v_u_1, (ref 6): v_u_16, (ref 7): v_u_3 ]]
            local function f_response(p59, p60, p61) --[[ Name: response ]] --[[ Line: 149 ]]
                --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_7, (copy 3): p_u_56 ]]
                p_u_23._evt:fire_event_to_client(v_u_7.EVT_ArtistEvent_ShopPurchase_Server, p_u_56, p59, p60, p61 == nil and {} or p61)
            end;
            p_u_23._player_blob_manager:get_verified_cached_blob(p_u_56.UserId, function(p62) --[[ Line: 153 ]]
                --[[ Upvalues: (ref 1): v_u_4, (ref 2): p_u_23, (copy 3): p_u_57, (copy 4): f_response, (copy 5): p_u_58, (ref 6): v_u_10, (ref 7): v_u_1, (ref 8): v_u_16, (ref 9): v_u_3, (copy 10): p_u_56, (ref 11): v_u_7 ]]
                local v63, v64 = v_u_4:is_event_active(p_u_23._api:get_day_event_list())
                if v63 ~= true or v64 ~= p_u_57 then
                    return f_response(false, "Expected event was not active");
                end;
                if v_u_4:playerblob_needs_event_info_validate(p62, v64) then
                    return f_response(false, "Event id out of date");
                end;
                local v65 = v_u_4:get_event_info(v64):get_shop_items_list():get(p_u_58)
                if v65 == nil then
                    return f_response(false, "Did not find item_id");
                end;
                if v_u_4:can_playerblob_claim_shop_item(p62, v65) ~= true then
                    return f_response(false, "Could not claim item");
                end;
                if v_u_4:playerblob_get_event_points(p62) < v65:get_price() then
                    return f_response(false, "Not enough event points");
                end;
                local v66 = v65:to_reward_description_info()
                if v66:can_playerblob_add(p62) ~= true then
                    return f_response(false, "Cannot add");
                end;
                if v65:get_type() == v_u_4.ShopItemType.Equipment and v_u_10:playerblob_can_add_more_gear(p62) ~= true then
                    return f_response(false, "Max gear owned");
                end;
                local v67 = v_u_4:playerblob_get_event_points(p62) - v65:get_price()
                v_u_1:is_int_greater_than(v67, -1)
                v_u_4:playerblob_set_event_points(p62, v67)
                v_u_4:playerblob_set_item_id_claimed(p62, v65:get_item_id())
                local v_u_68 = v_u_16:claim_reward_info_list_to_playerblob(p_u_23, p62, v_u_3:new({ v66 }))
                v_u_16:server_sync_reward_params(p_u_23, p_u_56, v_u_68, function(p69) --[[ Line: 191 ]]
                    --[[ Upvalues: (ref 1): v_u_16, (copy 2): v_u_68, (ref 3): p_u_23, (ref 4): v_u_7, (ref 5): p_u_56 ]]
                    local v70 = v_u_16.RewardInfo:list_to_table(v_u_16:reward_params_get_resolved_reward_list(v_u_68))
                    p_u_23._evt:fire_event_to_client(v_u_7.EVT_ArtistEvent_ShopPurchase_Server, p_u_56, true, p69, v70 == nil and {} or v70)
                end)
            end)
        end)
        p_u_23._evt:wait_on_event(v_u_7.EVT_ArtistEvent_BuyEventPointStars_Client, function(p_u_71, p72) --[[ Line: 197 ]]
            --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_7, (ref 3): v_u_4, (ref 4): v_u_5, (ref 5): v_u_16 ]]
            local function f_response(p73, p74, p75) --[[ Name: response ]] --[[ Line: 198 ]]
                --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_7, (copy 3): p_u_71 ]]
                p_u_23._evt:fire_event_to_client(v_u_7.EVT_ArtistEvent_BuyEventPointStars_ServerResponse, p_u_71, p73, p74, p75 == nil and {} or p75)
            end;
            if v_u_4:get_star_purchase_id_to_info():contains(p72) ~= true then
                return f_response(false, "invalid id");
            end;
            local v_u_76 = v_u_4:get_star_purchase_id_to_info():get(p72)
            p_u_23._player_blob_manager:get_verified_cached_blob(p_u_71.UserId, function(p77) --[[ Line: 205 ]]
                --[[ Upvalues: (ref 1): v_u_4, (ref 2): p_u_23, (ref 3): v_u_5, (copy 4): v_u_76, (copy 5): f_response, (ref 6): v_u_16, (copy 7): p_u_71, (ref 8): v_u_7 ]]
                local v78, v79 = v_u_4:is_event_active(p_u_23._api:get_day_event_list())
                if v78 then
                    v_u_4:playerblob_validate_event_info(p77, v79)
                    if v_u_5:get_star_currency(p77) < v_u_76:get_star_amount() then
                        return f_response(false, "Not enough stars");
                    end;
                    v_u_5:add_star_currency(p77, -v_u_76:get_star_amount())
                    v_u_16:server_sync_reward_params(p_u_23, p_u_71, v_u_16:claim_reward_info_list_to_playerblob(p_u_23, p77, (v_u_76:get_reward_desc_info_list())), function(p80, _, p81) --[[ Line: 219 ]]
                        --[[ Upvalues: (ref 1): v_u_16, (ref 2): p_u_23, (ref 3): v_u_7, (ref 4): p_u_71 ]]
                        local v82 = v_u_16.RewardInfo:list_to_table(p81)
                        p_u_23._evt:fire_event_to_client(v_u_7.EVT_ArtistEvent_BuyEventPointStars_ServerResponse, p_u_71, true, p80, v82 == nil and {} or v82)
                    end)
                else
                    local v83 = nil
                    p_u_23._evt:fire_event_to_client(v_u_7.EVT_ArtistEvent_BuyEventPointStars_ServerResponse, p_u_71, false, "no active event", v83 == nil and {} or v83)
                end;
            end)
        end)
        p_u_23._evt:wait_on_event(v_u_7.EVT_ArtistEvent_BuySong_Client, function(p_u_84, p_u_85) --[[ Line: 229 ]]
            --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_7, (ref 3): v_u_4, (ref 4): v_u_5, (ref 5): v_u_1 ]]
            local function f_response(p86, p87) --[[ Name: response ]] --[[ Line: 230 ]]
                --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_7, (copy 3): p_u_84 ]]
                p_u_23._evt:fire_event_to_client(v_u_7.EVT_ArtistEvent_BuySong_Server, p_u_84, p86, p87)
            end;
            local v88, v89 = v_u_4:is_event_active(p_u_23._api:get_day_event_list())
            if v88 ~= true then
                return f_response(false, "No active event");
            end;
            local v90, v_u_91 = v_u_4:get_eventid_songkey_purchase_info(v89, p_u_85)
            if v90 ~= true then
                return f_response(false, "Cannot buy");
            end;
            p_u_23._player_blob_manager:get_verified_cached_blob(p_u_84.UserId, function(p92) --[[ Line: 242 ]]
                --[[ Upvalues: (ref 1): v_u_5, (copy 2): p_u_85, (copy 3): f_response, (copy 4): v_u_91, (ref 5): v_u_4, (ref 6): v_u_1, (ref 7): p_u_23, (copy 8): p_u_84, (ref 9): v_u_7 ]]
                if v_u_5:get_song_key_owned_count(p92, p_u_85) ~= 0 then
                    return f_response(false, "Already owns song");
                end;
                if v_u_91 > v_u_4:playerblob_get_event_points(p92) then
                    return f_response(false, "Not enough event points");
                end;
                local v93 = v_u_4:playerblob_get_event_points(p92) - v_u_91
                v_u_1:is_true(v93 >= 0)
                v_u_4:playerblob_set_event_points(p92, v93)
                v_u_5:add_song(p92, p_u_85)
                p_u_23._player_blob_manager:enqueue_blob_sync_request(p_u_84.UserId, v_u_5.PlayerBlobRequestType.Write, function() --[[ Line: 259 ]]
                    --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_7, (ref 3): p_u_84 ]]
                    p_u_23._evt:fire_event_to_client(v_u_7.EVT_ArtistEvent_BuySong_Server, p_u_84, true, "")
                end)
            end)
        end)
    end;
    v24.write_special_event_data_for_play = function(_, p94, p95, _, _, p96, p97, _) --[[ Name: write_special_event_data_for_play ]] --[[ Line: 267 ]]
        --[[ Upvalues: (ref 1): v_u_14, (copy 2): p_u_23, (ref 3): v_u_4, (ref 4): v_u_11, (copy 5): v_u_25, (ref 6): v_u_9, (ref 7): v_u_6, (ref 8): v_u_2, (ref 9): v_u_15, (ref 10): v_u_8, (ref 11): v_u_22 ]]
        if p96._accuracy < v_u_14.MIN_ACCURACY_FOR_REWARDS_PCT or p96._early_quit == true then
            return;
        else
            local l__id_0 = p96._id
            local v98 = p_u_23._player_manager:id_to_player(l__id_0)
            local v99 = p_u_23._player_blob_manager:get_cached_blob(l__id_0)
            if v99 ~= nil and v98 ~= nil then
                local v100, v_u_101 = v_u_4:is_event_active(p_u_23._api:get_day_event_list())
                if v100 and v_u_4:get_event_point_reward_song_set(v_u_101):contains(p95) then
                    if v_u_11.EventLeaderboardsEnabled == true then
                        v_u_25:rbxid_add_play_for_song_key(p94, p96._id, p95, p96._score, p96._naked_score <= 0 and 1 or p96:get_gear_multiplier())
                    end;
                    local v102 = v_u_9:YForPointOf2PtLineP1P2X(60, v_u_4:get_play_event_point_count(), 360, v_u_4:get_play_event_point_count() * 6, v_u_6:singleton():songkey_get_approx_length_sec(p95)) * v_u_9:YForPointOf2PtLineP1P2X(0.35, 0.25, 0.85, 1, p96._accuracy)
                    local v103 = p_u_23._game_instance_manager:get_reward_cooldown_manager():get_play_count_for_userid(p96._id)
                    if v103 > 5 then
                        v102 = v102 * v_u_9:YForPointOf2PtLineP1P2X(5, 1, 20, 0, v103)
                    end;
                    local v104 = math.floor((v_u_2:clamp(v102, 0, v_u_4:get_play_event_point_count() * 6)))
                    v104 = v104
                    local v105, v_u_106
                    if v_u_15:playerblob_is_bonus_id_active_for_weekid(v99, v_u_15.BonusType.MoreEventPoints, p_u_23._api:get_week_id()) then
                        v105 = math.floor(v104 * 0.25)
                        v_u_106 = v104 + v105
                    else
                        v_u_106 = v104
                        v105 = 0
                    end;
                    local v107
                    if v_u_8:playerblob_has_vip_for_current_day(v99, p_u_23._api:get_day_id()) then
                        v107 = math.ceil(v104 * 0.1)
                        v_u_106 = v_u_106 + v107
                    else
                        v107 = 0
                    end;
                    local l__like_count_0 = p96._like_count
                    p97:push_back(function(p108) --[[ Line: 321 ]]
                        --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_101, (ref 3): v_u_106, (copy 4): l__like_count_0, (ref 5): v_u_22 ]]
                        v_u_4:playerblob_validate_event_info(p108, v_u_101)
                        v_u_4:playerblob_set_event_points(p108, v_u_4:playerblob_get_event_points(p108) + v_u_106)
                        if l__like_count_0 > 0 then
                            v_u_4:playerblob_set_event_points(p108, v_u_4:playerblob_get_event_points(p108) + v_u_22 * l__like_count_0)
                        end;
                    end)
                    local v109 = p_u_23._chat:get_chat_service()
                    local v110 = p_u_23._chat:gameid_get_channel(p94._game_id)
                    if v109 and v110 then
                        local v111 = v105 <= 0 and "" or string.format(" (+%d Team Bonus)", v105)
                        if v107 > 0 then
                            v111 = string.format(" (+%d VIP Bonus)", v107)
                        end;
                        v109:send_system_message_to_player_for_channel(v98, v110, string.format("You have earned %d event points for playing this song.%s", v_u_106, v111), function(p112) --[[ Line: 344 ]]
                            --[[ Upvalues: (ref 1): v_u_2 ]]
                            p112:set_icon(v_u_2:important_assetid())
                        end)
                        if l__like_count_0 > 0 then
                            v109:send_system_message_to_player_for_channel(v98, v110, string.format("You have earned %d event points from cheers.", v_u_22 * l__like_count_0), function(p113) --[[ Line: 354 ]]
                                --[[ Upvalues: (ref 1): v_u_2 ]]
                                p113:set_icon(v_u_2:important_assetid())
                            end)
                        end;
                    end;
                end;
            end;
        end;
    end;
    v24.player_disconnecting = function(_, p114) --[[ Name: player_disconnecting ]] --[[ Line: 364 ]]
        --[[ Upvalues: (ref 1): v_u_11, (copy 2): v_u_25, (copy 3): v_u_27, (copy 4): v_u_28, (copy 5): v_u_26 ]]
        if v_u_11.EventLeaderboardsEnabled == true then
            v_u_25:player_disconnecting(p114)
        end;
        v_u_27:remove(p114)
        v_u_28:remove(p114)
        if v_u_11.PetAssignmentEnabled == true then
            v_u_26:player_disconnecting(p114)
        end;
    end;
    v24.update = function(_, p115) --[[ Name: update ]] --[[ Line: 375 ]]
        --[[ Upvalues: (ref 1): v_u_11, (copy 2): v_u_25 ]]
        if v_u_11.EventLeaderboardsEnabled == true then
            v_u_25:update(p115)
        end;
    end;
    v24.can_playerid_start_songkey = function(_, _, p116, _) --[[ Name: can_playerid_start_songkey ]] --[[ Line: 381 ]]
        --[[ Upvalues: (copy 1): v_u_25 ]]
        return v_u_25:get_active_event_songkey() == p116;
    end;
    f_cons()
    return v24;
end;
return v19;
