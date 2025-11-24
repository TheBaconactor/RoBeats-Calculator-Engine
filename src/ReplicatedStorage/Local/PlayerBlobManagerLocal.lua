-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:26 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_4 = require(game.ReplicatedStorage.Local.DebugOut)
local v_u_5 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_6 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
local v_u_7 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_8 = require(game.ReplicatedStorage.Shared.Constants)
local v_u_9 = require(game.ReplicatedStorage.PlayerInfo.DayEventInfo)
local v_u_10 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_11 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_12 = require(game.ReplicatedStorage.SPChat.Shared.SPChatMessage)
local v_u_13 = require(game.ReplicatedStorage.Shared.FavoriteData)
local v_u_14 = require(game.ReplicatedStorage.PlayerInfo.SpecialEventInfo)
require(game.ReplicatedStorage.Shared.MissionInfo)
local v_u_15 = require(game.ReplicatedStorage.Shared.Mission.MissionActiveData)
local v_u_16 = require(game.ReplicatedStorage.PlayerInfo.Collection.CollectionInfo)
require(game.ReplicatedStorage.PlayerInfo.ChallengePassV2.ChallengePassV2Data)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_17 = require(game.ReplicatedStorage.Shared.SPDict)
local v18 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_19 = nil
v18:require_client(function() --[[ Line: 24 ]]
    --[[ Upvalues: (ref 1): v_u_19 ]]
    v_u_19 = require(game.ReplicatedStorage.Lobby.UI.ArtistEventUI.ArtistEventUITab_PetAssignment)
end)
return {
    ["new"] = function(_, p_u_20) --[[ Name: new ]] --[[ Line: 30 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_3, (copy 3): v_u_9, (copy 4): v_u_13, (copy 5): v_u_10, (copy 6): v_u_15, (copy 7): v_u_16, (copy 8): v_u_17, (copy 9): v_u_2, (copy 10): v_u_11, (copy 11): v_u_7, (copy 12): v_u_4, (copy 13): v_u_8, (ref 14): v_u_19, (copy 15): v_u_12, (copy 16): v_u_14, (copy 17): v_u_5, (copy 18): v_u_6 ]]
        local v_u_21 = {}
        local v_u_22 = v_u_1:new()
        local v_u_23 = false
        local v_u_24 = false
        local v_u_25 = v_u_3:new()
        local v_u_26 = 0
        local v_u_27 = 0
        local v_u_28 = v_u_9.EventList:default_list()
        local v_u_29 = 0
        local v_u_30 = false
        local v_u_31 = nil
        local v_u_32 = v_u_3:new()
        local v_u_33 = v_u_3:new()
        local s_MarketplaceService_0 = game:GetService("MarketplaceService")
        local v_u_34 = 0
        local v_u_35 = 0
        local v_u_36 = 0
        local v_u_37 = 0
        local v_u_38 = 0
        local v_u_39 = 0
        local v_u_40 = -1
        v_u_21.get_dayid = function(_) --[[ Name: get_dayid ]] --[[ Line: 57 ]]
            --[[ Upvalues: (ref 1): v_u_34 ]]
            return v_u_34;
        end;
        v_u_21.get_weekid = function(_) --[[ Name: get_weekid ]] --[[ Line: 58 ]]
            --[[ Upvalues: (ref 1): v_u_35 ]]
            return v_u_35;
        end;
        v_u_21.get_monthid = function(_) --[[ Name: get_monthid ]] --[[ Line: 59 ]]
            --[[ Upvalues: (ref 1): v_u_36 ]]
            return v_u_36;
        end;
        v_u_21.get_day_id = function(_) --[[ Name: get_day_id ]] --[[ Line: 62 ]]
            --[[ Upvalues: (ref 1): v_u_34 ]]
            return v_u_34;
        end;
        v_u_21.get_week_id = function(_) --[[ Name: get_week_id ]] --[[ Line: 63 ]]
            --[[ Upvalues: (ref 1): v_u_35 ]]
            return v_u_35;
        end;
        v_u_21.get_month_id = function(_) --[[ Name: get_month_id ]] --[[ Line: 64 ]]
            --[[ Upvalues: (ref 1): v_u_36 ]]
            return v_u_36;
        end;
        v_u_21.get_time_to_next_day_sec = function(_) --[[ Name: get_time_to_next_day_sec ]] --[[ Line: 66 ]]
            --[[ Upvalues: (ref 1): v_u_37 ]]
            return v_u_37;
        end;
        v_u_21.get_time_to_next_week_sec = function(_) --[[ Name: get_time_to_next_week_sec ]] --[[ Line: 67 ]]
            --[[ Upvalues: (ref 1): v_u_38 ]]
            return v_u_38;
        end;
        v_u_21.get_time_to_next_month_sec = function(_) --[[ Name: get_time_to_next_month_sec ]] --[[ Line: 68 ]]
            --[[ Upvalues: (ref 1): v_u_39 ]]
            return v_u_39;
        end;
        v_u_21.get_server_id = function(_) --[[ Name: get_server_id ]] --[[ Line: 69 ]]
            --[[ Upvalues: (ref 1): v_u_40 ]]
            return v_u_40;
        end;
        local v_u_41 = {}
        v_u_21.get_cached_server_info_table = function(_) --[[ Name: get_cached_server_info_table ]] --[[ Line: 72 ]]
            --[[ Upvalues: (ref 1): v_u_41 ]]
            return v_u_41;
        end;
        local v_u_42 = v_u_13:new(v_u_10:get_local_userid())
        local v_u_43 = false
        local v_u_44 = v_u_15:new(-1, -1)
        local v_u_45 = {}
        local v_u_46 = {}
        v_u_21.get_server_mission_data = function(_) --[[ Name: get_server_mission_data ]] --[[ Line: 81 ]]
            --[[ Upvalues: (ref 1): v_u_44 ]]
            return v_u_44:to_table(), v_u_44;
        end;
        v_u_21.get_server_mission_active_data = function(_) --[[ Name: get_server_mission_active_data ]] --[[ Line: 82 ]]
            --[[ Upvalues: (ref 1): v_u_44 ]]
            return v_u_44;
        end;
        v_u_21.get_server_leaderboard_data = function(_) --[[ Name: get_server_leaderboard_data ]] --[[ Line: 83 ]]
            --[[ Upvalues: (ref 1): v_u_45 ]]
            return v_u_45;
        end;
        v_u_21.get_server_song_shop_available_items_data = function(_) --[[ Name: get_server_song_shop_available_items_data ]] --[[ Line: 84 ]]
            --[[ Upvalues: (ref 1): v_u_46 ]]
            return v_u_46;
        end;
        local v_u_47 = v_u_16:new()
        v_u_21.get_cached_collection_info = function(_) --[[ Name: get_cached_collection_info ]] --[[ Line: 87 ]]
            --[[ Upvalues: (ref 1): v_u_47 ]]
            return v_u_47;
        end;
        local v_u_48 = v_u_17:new()
        v_u_21.get_liked_web_npc_id_set = function(_) --[[ Name: get_liked_web_npc_id_set ]] --[[ Line: 90 ]]
            --[[ Upvalues: (copy 1): v_u_48 ]]
            return v_u_48;
        end;
        local function f_cons() --[[ Name: cons ]] --[[ Line: 92 ]]
            --[[ Upvalues: (copy 1): p_u_20, (ref 2): v_u_2, (ref 3): v_u_11, (ref 4): v_u_27, (ref 5): v_u_34, (ref 6): v_u_35, (ref 7): v_u_36, (ref 8): v_u_37, (ref 9): v_u_38, (ref 10): v_u_39, (ref 11): v_u_40, (ref 12): v_u_7, (ref 13): v_u_41, (ref 14): v_u_44, (ref 15): v_u_15, (ref 16): v_u_45, (ref 17): v_u_46, (ref 18): v_u_1, (copy 19): v_u_22, (ref 20): v_u_47, (ref 21): v_u_16, (ref 22): v_u_28, (ref 23): v_u_9, (ref 24): v_u_23, (ref 25): v_u_26, (ref 26): v_u_24, (ref 27): v_u_4, (copy 28): v_u_25, (copy 29): v_u_32, (copy 30): v_u_21, (ref 31): v_u_29, (ref 32): v_u_8, (ref 33): v_u_30, (ref 34): v_u_42, (ref 35): v_u_13, (ref 36): v_u_43, (ref 37): v_u_19, (copy 38): v_u_48, (ref 39): v_u_10, (ref 40): v_u_12, (ref 41): v_u_14 ]]
            p_u_20._evt:wait_on_event(v_u_2.EVT_PlayerBlob_ServerBlobSync, function(p49, p50, p51, p52, p53) --[[ Line: 93 ]]
                --[[ Upvalues: (ref 1): v_u_11, (ref 2): v_u_27, (ref 3): v_u_34, (ref 4): v_u_35, (ref 5): v_u_36, (ref 6): v_u_37, (ref 7): v_u_38, (ref 8): v_u_39, (ref 9): v_u_40, (ref 10): v_u_7, (ref 11): p_u_20, (ref 12): v_u_41, (ref 13): v_u_44, (ref 14): v_u_15, (ref 15): v_u_45, (ref 16): v_u_46, (ref 17): v_u_1, (ref 18): v_u_22, (ref 19): v_u_47, (ref 20): v_u_16, (ref 21): v_u_28, (ref 22): v_u_9, (ref 23): v_u_23, (ref 24): v_u_26, (ref 25): v_u_24, (ref 26): v_u_4, (ref 27): v_u_25, (ref 28): v_u_2 ]]
                v_u_11:is_number(p52.GlobalTime)
                v_u_11:is_int(p52.DayID)
                v_u_11:is_int(p52.WeekID)
                v_u_11:is_int(p52.MonthID)
                v_u_27 = p52.GlobalTime
                v_u_34 = p52.DayID
                v_u_35 = p52.WeekID
                v_u_36 = p52.MonthID
                v_u_37 = p52.TimeToNextDaySec
                v_u_38 = p52.TimeToNextWeekSec
                v_u_39 = p52.TimeToNextMonthSec
                v_u_40 = p52.ServerID
                v_u_7:singleton():set_server_id(v_u_40)
                p_u_20._guild_manager:handle_player_info_server_response(p50.IsInGuild, p50.GuildID)
                v_u_41 = p53
                if p53.MissionData then
                    v_u_44 = v_u_15:from_table(p53.MissionData)
                end;
                if p53.LeaderboardInfo then
                    v_u_45 = p53.LeaderboardInfo
                end;
                if p53.SongShopData and p53.SongShopData.AvailableItems then
                    v_u_46 = p53.SongShopData.AvailableItems
                end;
                v_u_1:update_from_json(v_u_22, p49)
                v_u_47 = v_u_16:get_collection_info_from_playerblob(v_u_22)
                v_u_28 = v_u_9.EventList:from_table(p51)
                v_u_23 = true
                v_u_26 = tick()
                p_u_20._player_settings_manager:update_from_json_str(p_u_20, v_u_1:get_player_settings_str(v_u_22))
                if v_u_24 ~= true then
                    p_u_20._player_settings_manager:initial_settings_sync_update(p_u_20)
                end;
                v_u_4:puts("PlayerBlob ServerBlobSync time(%.2f)", v_u_26)
                for v54 = 1, v_u_25:count() do
                    v_u_25:get(v54)(v_u_22)
                end;
                v_u_25:clear()
                if v_u_24 ~= true then
                    v_u_24 = true
                    p_u_20._evt:fire_event_to_server(v_u_2.EVT_StartupFetchMiscData)
                end;
            end)
            p_u_20._evt:wait_on_event(v_u_2.EVT_Shop_IAPFinished, function(p55, p56, p57, p58) --[[ Line: 147 ]]
                --[[ Upvalues: (ref 1): v_u_32, (ref 2): v_u_23, (ref 3): v_u_21 ]]
                v_u_32:push_back({
                    p55,
                    p56,
                    p57,
                    p58
                })
                v_u_23 = false
                v_u_21:iap_finish_update()
            end)
            p_u_20._evt:wait_on_event(v_u_2.EVT_PlayerBlob_ServerRaiseSyncFail, function() --[[ Line: 153 ]]
                --[[ Upvalues: (ref 1): v_u_23, (ref 2): v_u_29, (ref 3): v_u_8, (ref 4): v_u_30 ]]
                v_u_23 = false
                v_u_29 = v_u_8.WAIT_SYNC_POPUP_TIME_SEC
                v_u_30 = true
            end)
            p_u_20._evt:wait_on_event_once(v_u_2.EVT_FavoriteData_ServerResponse, function(p59) --[[ Line: 159 ]]
                --[[ Upvalues: (ref 1): v_u_42, (ref 2): v_u_13, (ref 3): v_u_43 ]]
                v_u_42 = v_u_13:from_table(p59)
                v_u_43 = true
            end)
            p_u_20._evt:wait_on_event(v_u_2.EVT_PetAssignment_ServerPushData, function(p60) --[[ Line: 164 ]]
                --[[ Upvalues: (ref 1): v_u_19, (ref 2): p_u_20 ]]
                v_u_19:handle_server_push_data(p_u_20, p60)
            end)
            p_u_20._evt:wait_on_event(v_u_2.EVT_WebNPC_ServerSendLikedWebNPCSet, function(p61) --[[ Line: 168 ]]
                --[[ Upvalues: (ref 1): v_u_48 ]]
                v_u_48:add_set_from_table_list(p61)
            end)
            game:GetService("TeleportService").TeleportInitFailed:Connect(function(p62, p63, p64) --[[ Line: 172 ]]
                --[[ Upvalues: (ref 1): v_u_10, (ref 2): v_u_4, (ref 3): p_u_20, (ref 4): v_u_12 ]]
                if p62.UserId == v_u_10:get_local_userid() then
                    local v65 = string.format("Teleport Failed: %s. %s", tostring(p63), (tostring(p64)))
                    v_u_4:warnf(v65)
                    p_u_20._chat:get_system_channel():add_message_to_channel(v_u_12:new(v65):set_icon(v_u_10:gear_assetid()))
                end;
            end)
            p_u_20._evt:wait_on_event(v_u_2.EVT_SpecialEvent_ServerNotifyPlayerDataUpdated, function(p66) --[[ Line: 180 ]]
                --[[ Upvalues: (ref 1): v_u_14 ]]
                v_u_14:update_player_event_data(p66)
            end)
        end;
        local function _() --[[ Name: has_iap_queued_fns ]] --[[ Line: 186 ]]
            --[[ Upvalues: (copy 1): v_u_32, (copy 2): v_u_33 ]]
            return v_u_32:count() > 0 and true or v_u_33:count() > 0;
        end;
        local function _() --[[ Name: clear_iap_queued_fns ]] --[[ Line: 190 ]]
            --[[ Upvalues: (copy 1): v_u_32, (copy 2): v_u_33 ]]
            v_u_32:clear()
            v_u_33:clear()
        end;
        v_u_21.prompt_product_purchase = function(_, p67) --[[ Name: prompt_product_purchase ]] --[[ Line: 195 ]]
            --[[ Upvalues: (copy 1): s_MarketplaceService_0 ]]
            s_MarketplaceService_0:PromptProductPurchase(game.Players.LocalPlayer, p67)
        end;
        v_u_21.set_iap_finish_fn = function(p68, p69) --[[ Name: set_iap_finish_fn ]] --[[ Line: 199 ]]
            --[[ Upvalues: (copy 1): v_u_33 ]]
            v_u_33:clear()
            v_u_33:push_back(p69)
            p68:iap_finish_update()
        end;
        v_u_21.iap_finish_update = function(p70) --[[ Name: iap_finish_update ]] --[[ Line: 205 ]]
            --[[ Upvalues: (copy 1): v_u_33, (copy 2): v_u_32 ]]
            if v_u_33:count() > 0 and v_u_32:count() > 0 then
                local v_u_71 = v_u_33:pop_front()
                local v72 = v_u_32:pop_front()
                local v_u_73 = v72[1]
                local v_u_74 = v72[2]
                local v_u_75 = v72[3]
                local v_u_76 = v72[4]
                p70:do_sync(function() --[[ Line: 210 ]]
                    --[[ Upvalues: (copy 1): v_u_71, (copy 2): v_u_73, (copy 3): v_u_74, (copy 4): v_u_75, (copy 5): v_u_76 ]]
                    v_u_71(v_u_73, v_u_74, v_u_75, v_u_76)
                end)
            end;
        end;
        v_u_21.is_synced = function(_) --[[ Name: is_synced ]] --[[ Line: 216 ]]
            --[[ Upvalues: (ref 1): v_u_23 ]]
            return v_u_23;
        end;
        v_u_21.get_synced_time = function(_) --[[ Name: get_synced_time ]] --[[ Line: 220 ]]
            --[[ Upvalues: (ref 1): v_u_26 ]]
            return v_u_26;
        end;
        v_u_21.get_player_blob = function(_) --[[ Name: get_player_blob ]] --[[ Line: 224 ]]
            --[[ Upvalues: (copy 1): v_u_22 ]]
            return v_u_22;
        end;
        v_u_21.get_day_event_list = function(_) --[[ Name: get_day_event_list ]] --[[ Line: 228 ]]
            --[[ Upvalues: (ref 1): v_u_28 ]]
            return v_u_28;
        end;
        local v_u_77 = false
        v_u_21.do_sync = function(_, p78) --[[ Name: do_sync ]] --[[ Line: 233 ]]
            --[[ Upvalues: (ref 1): v_u_23, (ref 2): v_u_29, (ref 3): v_u_30, (copy 4): v_u_25, (ref 5): v_u_77, (copy 6): p_u_20, (ref 7): v_u_2, (ref 8): v_u_4 ]]
            v_u_23 = false
            v_u_29 = 0
            v_u_30 = true
            if p78 ~= nil then
                v_u_25:push_back(p78)
            end;
            if v_u_77 == false then
                v_u_77 = true
                p_u_20._evt:fire_event_to_server(v_u_2.EVT_PlayerBlob_ClientInitialRequestSync)
                v_u_4:puts("sending PlayerBlob Client InitialRequestSync")
            else
                p_u_20._evt:fire_event_to_server(v_u_2.EVT_PlayerBlob_ClientRequestSync)
                v_u_4:puts("sending PlayerBlob Client RequestSync")
            end;
        end;
        v_u_21.update = function(_, p79) --[[ Name: update ]] --[[ Line: 252 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_27, (ref 3): v_u_38, (ref 4): v_u_37, (ref 5): v_u_39, (ref 6): v_u_23, (ref 7): v_u_29, (ref 8): v_u_30, (ref 9): v_u_31, (ref 10): v_u_8, (copy 11): p_u_20, (ref 12): v_u_6 ]]
            local v80 = v_u_5:TimescaleToDeltaTime(p79)
            v_u_27 = v_u_27 + v80
            v_u_38 = math.max(v_u_38 - v80, 0)
            v_u_37 = math.max(v_u_37 - v80, 0)
            v_u_39 = math.max(v_u_39 - v80)
            if v_u_23 == true then
                v_u_30 = false
            else
                v_u_29 = v_u_29 + v80
                if v_u_30 == true and (v_u_31 == nil and v_u_29 > v_u_8.WAIT_SYNC_POPUP_TIME_SEC) then
                    v_u_31 = p_u_20._menus:push_menu(v_u_6:new(p_u_20, p_u_20._spui, p_u_20._menus):set_on_close_fn(function() --[[ Line: 266 ]]
                        --[[ Upvalues: (ref 1): p_u_20, (ref 2): v_u_31 ]]
                        p_u_20._menus:remove_menu(v_u_31)
                        v_u_31 = nil
                    end))
                    v_u_30 = false
                end;
            end;
            if v_u_31 ~= nil then
                v_u_31:set_text("Attempting to connect to server...", string.format("The server may be down for maintenance. Try joining the game again, or re-trying at later time. Waiting for (%d) seconds.", (math.floor(v_u_29))))
            end;
            if v_u_31 ~= nil and v_u_23 == true then
                p_u_20._menus:remove_menu(v_u_31)
                v_u_31 = nil
            end;
        end;
        v_u_21.get_global_time = function(_) --[[ Name: get_global_time ]] --[[ Line: 291 ]]
            --[[ Upvalues: (ref 1): v_u_27 ]]
            return math.floor(v_u_27);
        end;
        v_u_21.get_global_time_float = function(_) --[[ Name: get_global_time_float ]] --[[ Line: 292 ]]
            --[[ Upvalues: (ref 1): v_u_27 ]]
            return v_u_27;
        end;
        local v_u_81 = v_u_3:new()
        v_u_21.add_recently_acquired_songid = function(_, p82) --[[ Name: add_recently_acquired_songid ]] --[[ Line: 295 ]]
            --[[ Upvalues: (copy 1): v_u_81, (ref 2): v_u_7 ]]
            if not v_u_81:contains(p82) then
                if v_u_7:singleton():contains_key(p82) then
                    v_u_81:push_front(p82)
                end;
            end;
        end;
        v_u_21.remove_recently_acquired_songid = function(_, p83) --[[ Name: remove_recently_acquired_songid ]] --[[ Line: 302 ]]
            --[[ Upvalues: (copy 1): v_u_81 ]]
            v_u_81:remove(p83)
        end;
        v_u_21.get_recently_acquired_songids_list = function(_) --[[ Name: get_recently_acquired_songids_list ]] --[[ Line: 306 ]]
            --[[ Upvalues: (copy 1): v_u_81 ]]
            return v_u_81;
        end;
        v_u_21.get_song_favorite_data = function(_) --[[ Name: get_song_favorite_data ]] --[[ Line: 310 ]]
            --[[ Upvalues: (ref 1): v_u_42 ]]
            return v_u_42;
        end;
        v_u_21.is_songkey_favorite = function(_, p84) --[[ Name: is_songkey_favorite ]] --[[ Line: 311 ]]
            --[[ Upvalues: (ref 1): v_u_42 ]]
            return v_u_42:is_song_in_list(p84);
        end;
        v_u_21.is_favorite_data_loaded = function(_) --[[ Name: is_favorite_data_loaded ]] --[[ Line: 312 ]]
            --[[ Upvalues: (ref 1): v_u_43 ]]
            return v_u_43;
        end;
        v_u_21.add_song_to_favorites = function(_, p85, p_u_86) --[[ Name: add_song_to_favorites ]] --[[ Line: 313 ]]
            --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_4, (copy 3): p_u_20, (ref 4): v_u_6, (ref 5): v_u_2, (ref 6): v_u_42, (ref 7): v_u_13 ]]
            if v_u_7:singleton():contains_key(p85) ~= true then
                return v_u_4:warnf("add_song_to_favorites(%s)", (tostring(p85)));
            end;
            local v_u_87 = p_u_20._menus:push_menu(v_u_6:new(p_u_20, p_u_20._spui, p_u_20._menus)):set_text("Updating Favorites", "Please wait..."):set_close_button_visible(false)
            p_u_20._evt:wait_on_event_once(v_u_2.EVT_FavoriteData_ServerAddSongResponse, function(p88, p89, p90) --[[ Line: 320 ]]
                --[[ Upvalues: (ref 1): p_u_20, (copy 2): v_u_87, (ref 3): v_u_42, (ref 4): v_u_13, (ref 5): v_u_6, (copy 6): p_u_86 ]]
                p_u_20._menus:remove_menu(v_u_87)
                if p88 == true then
                    v_u_42 = v_u_13:from_table(p90)
                else
                    p_u_20._menus:push_menu(v_u_6:new(p_u_20, p_u_20._spui, p_u_20._menus)):set_text("Error", p89)
                end;
                return p_u_86();
            end)
            p_u_20._evt:fire_event_to_server(v_u_2.EVT_FavoriteData_ClientAddSong, p85)
        end;
        v_u_21.test_time_to_next_day_and_update = function(_) --[[ Name: test_time_to_next_day_and_update ]] --[[ Line: 333 ]]
            --[[ Upvalues: (copy 1): p_u_20, (ref 2): v_u_6, (ref 3): v_u_5 ]]
            local l__spui_0 = p_u_20._spui
            local l__menus_0 = p_u_20._menus
            if p_u_20._player_blob_manager:get_time_to_next_day_sec() <= 0 then
                local v_u_91 = l__menus_0:push_menu(v_u_6:new(p_u_20, l__spui_0, l__menus_0):set_text("Loading...", "Please wait..."):set_close_button_visible(false))
                p_u_20._update_enqueue_fn:enqueue_function(function() --[[ Line: 341 ]]
                    --[[ Upvalues: (ref 1): p_u_20, (copy 2): l__menus_0, (copy 3): v_u_91 ]]
                    p_u_20._player_blob_manager:do_sync(function() --[[ Line: 342 ]]
                        --[[ Upvalues: (ref 1): l__menus_0, (ref 2): v_u_91 ]]
                        l__menus_0:remove_menu(v_u_91)
                    end)
                end, v_u_5:DeltaTimeToTimescale(2))
            end;
        end;
        f_cons()
        return v_u_21;
    end
};
