-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:01 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Local.DebugOut)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_5 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_6 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_7 = require(game.ReplicatedStorage.Shared.PlayerListEntry)
local v_u_8 = require(game.ReplicatedStorage.Shared.PlayerListActivity)
local v_u_9 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_10 = require(game.ReplicatedStorage.Shared.CooldownDelay)
local v_u_11 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_12 = require(game.ReplicatedStorage.Shared.PlayerStatus)
local v13 = {}
local l_All_0 = v_u_12.PlayerListFilterMode.All
local l_Time_0 = v_u_12.PlayerListOrderMode.Time
v13.new = function(_, p_u_14) --[[ Name: new ]] --[[ Line: 23 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_12, (copy 3): v_u_10, (copy 4): v_u_4, (copy 5): v_u_7, (copy 6): v_u_2, (copy 7): v_u_1, (ref 8): l_All_0, (copy 9): v_u_8, (ref 10): l_Time_0, (copy 11): v_u_9, (copy 12): v_u_5, (copy 13): v_u_11, (copy 14): v_u_6 ]]
    local v_u_15 = {}
    local v_u_16 = v_u_3:new()
    local v_u_17 = nil
    local v_u_18 = nil
    local function f_update_from_table_list(p19) --[[ Name: update_from_table_list ]] --[[ Line: 29 ]]
        --[[ Upvalues: (ref 1): v_u_12, (copy 2): v_u_16 ]]
        local v20 = v_u_12:tablelist_to_list(p19)
        for v21 = 1, v20:count() do
            local v22 = v20:get(v21)
            v22:set_last_modified(tick())
            v_u_16:add(v22:get_player_id(), v22)
        end;
    end;
    local v_u_23 = false
    v_u_15.is_playerlist_update_subscribed = function(_) --[[ Name: is_playerlist_update_subscribed ]] --[[ Line: 40 ]]
        --[[ Upvalues: (ref 1): v_u_23 ]]
        return v_u_23;
    end;
    local v_u_24 = v_u_3:new()
    local v_u_25 = -1
    local v_u_26 = -1
    local v_u_27 = v_u_10:new()
    local v_u_28 = v_u_4:new()
    local v_u_29 = false
    local v_u_30 = v_u_4:new()
    local v_u_31 = 0
    local v_u_32 = v_u_10:new()
    local v_u_33 = false
    local v_u_34 = 0
    local function f_update_playerlist_info_from_tablist(p35) --[[ Name: update_playerlist_info_from_tablist ]] --[[ Line: 56 ]]
        --[[ Upvalues: (ref 1): v_u_3, (copy 2): v_u_24, (ref 3): v_u_7, (ref 4): v_u_25 ]]
        local v36 = v_u_3:new():add_set_from_table_list(v_u_24:key_list():get_table())
        for _, v37 in v_u_7:table_to_list(p35):key_itr() do
            if v_u_24:contains(v37:get_player_id()) then
                v_u_24:get(v37:get_player_id()):copy_from_entry(v37)
                v36:remove(v37:get_player_id())
            else
                v_u_24:add(v37:get_player_id(), v37)
            end;
        end;
        for v38, _ in v36:key_itr() do
            v_u_24:remove(v38)
        end;
        v_u_25 = tick()
    end;
    local function f_cons() --[[ Name: cons ]] --[[ Line: 87 ]]
        --[[ Upvalues: (copy 1): p_u_14, (ref 2): v_u_2, (copy 3): f_update_from_table_list, (copy 4): v_u_16, (ref 5): v_u_17, (ref 6): v_u_18, (ref 7): v_u_12, (ref 8): v_u_23, (ref 9): v_u_1, (copy 10): f_update_playerlist_info_from_tablist, (copy 11): v_u_28, (copy 12): v_u_15, (ref 13): v_u_33 ]]
        p_u_14._evt:wait_on_event_once(v_u_2.EVT_PlayerStatus_ServerRespondInitial, function(p39) --[[ Line: 88 ]]
            --[[ Upvalues: (ref 1): f_update_from_table_list ]]
            f_update_from_table_list(p39)
        end)
        p_u_14._evt:fire_event_to_server(v_u_2.EVT_PlayerStatus_ClientRequestInitial)
        p_u_14._evt:wait_on_event(v_u_2.EVT_PlayerStatus_ServerUpdate, function(p40) --[[ Line: 93 ]]
            --[[ Upvalues: (ref 1): f_update_from_table_list ]]
            f_update_from_table_list(p40)
        end)
        game.Players.PlayerRemoving:connect(function(p41) --[[ Line: 97 ]]
            --[[ Upvalues: (ref 1): v_u_16 ]]
            v_u_16:remove(p41.UserId)
        end)
        local v42, v43 = v_u_12:backup_cleanup()
        v_u_17 = v42
        v_u_18 = v43
        p_u_14._evt:wait_on_event(v_u_2.EVT_Players_ServerSendPlayerListUpdate, function(p44) --[[ Line: 104 ]]
            --[[ Upvalues: (ref 1): v_u_23, (ref 2): v_u_1, (ref 3): f_update_playerlist_info_from_tablist, (ref 4): v_u_28, (ref 5): v_u_15, (ref 6): v_u_33 ]]
            if v_u_23 ~= true then
                return v_u_1:puts("Got EVT_Players_ServerSendPlayerListUpdate when not subscribed");
            end;
            f_update_playerlist_info_from_tablist(p44)
            for _, v45 in v_u_28:key_itr() do
                v45(v_u_15:get_cached_playerlist_info_list())
            end;
            v_u_28:clear()
            v_u_33 = false
        end)
    end;
    v_u_15.get_playerlist_updated_time = function(_) --[[ Name: get_playerlist_updated_time ]] --[[ Line: 124 ]]
        --[[ Upvalues: (ref 1): v_u_26, (ref 2): v_u_25, (copy 3): v_u_27 ]]
        if v_u_26 ~= v_u_25 and v_u_27:is_on_cooldown() ~= true then
            v_u_26 = v_u_25
            v_u_27:add_cooldown(2)
        end;
        return v_u_26;
    end;
    v_u_15.get_cached_playerlist_info_list = function(_) --[[ Name: get_cached_playerlist_info_list ]] --[[ Line: 147 ]]
        --[[ Upvalues: (ref 1): v_u_25, (ref 2): v_u_31, (ref 3): v_u_29, (copy 4): v_u_30, (copy 5): v_u_24, (ref 6): v_u_4, (ref 7): l_All_0, (ref 8): v_u_12, (ref 9): v_u_8, (ref 10): l_Time_0 ]]
        if v_u_25 ~= v_u_31 then
            v_u_29 = false
        end;
        if v_u_29 ~= true then
            v_u_30:clear()
            for _, v46 in v_u_24:key_itr() do
                v_u_30:push_back(v46)
            end;
            v_u_4:remove_if(v_u_30, function(p47) --[[ Line: 158 ]]
                --[[ Upvalues: (ref 1): l_All_0, (ref 2): v_u_12, (ref 3): v_u_8 ]]
                if l_All_0 == v_u_12.PlayerListFilterMode.Joinable then
                    return p47:get_activity() ~= v_u_8.MatchMaking;
                elseif l_All_0 == v_u_12.PlayerListFilterMode.Spectateable then
                    return p47:get_activity() ~= v_u_8.Match;
                else
                    return false;
                end;
            end)
            v_u_30:sort(function(p48, p49) --[[ Line: 168 ]]
                --[[ Upvalues: (ref 1): l_Time_0, (ref 2): v_u_12 ]]
                if l_Time_0 == v_u_12.PlayerListOrderMode.Time then
                    return p48:get_join_time() > p49:get_join_time();
                else
                    return string.lower(p48:get_name()) < string.lower(p49:get_name());
                end;
            end)
            v_u_29 = true
            v_u_31 = v_u_25
        end;
        return v_u_30;
    end;
    v_u_15.get_playerlist_filter_mode = function(_) --[[ Name: get_playerlist_filter_mode ]] --[[ Line: 182 ]]
        --[[ Upvalues: (ref 1): l_All_0 ]]
        return l_All_0;
    end;
    v_u_15.set_playerlist_filter_mode = function(_, p50) --[[ Name: set_playerlist_filter_mode ]] --[[ Line: 183 ]]
        --[[ Upvalues: (ref 1): v_u_9, (ref 2): v_u_12, (ref 3): l_All_0, (ref 4): v_u_29 ]]
        v_u_9:is_enum_member(p50, v_u_12.PlayerListFilterMode)
        l_All_0 = p50
        v_u_29 = false
    end;
    v_u_15.get_playerlist_order_mode = function(_) --[[ Name: get_playerlist_order_mode ]] --[[ Line: 189 ]]
        --[[ Upvalues: (ref 1): l_Time_0 ]]
        return l_Time_0;
    end;
    v_u_15.set_playerlist_order_mode = function(_, p51) --[[ Name: set_playerlist_order_mode ]] --[[ Line: 190 ]]
        --[[ Upvalues: (ref 1): v_u_9, (ref 2): v_u_12, (ref 3): l_Time_0, (ref 4): v_u_29 ]]
        v_u_9:is_enum_member(p51, v_u_12.PlayerListOrderMode)
        l_Time_0 = p51
        v_u_29 = false
    end;
    local v_u_52 = false
    local v_u_53 = false
    v_u_15.set_playerlist_info_update_subscribed = function(_, p54) --[[ Name: set_playerlist_info_update_subscribed ]] --[[ Line: 198 ]]
        --[[ Upvalues: (ref 1): v_u_9, (ref 2): v_u_52, (ref 3): v_u_53, (ref 4): v_u_29, (ref 5): l_All_0, (ref 6): v_u_12, (ref 7): l_Time_0, (ref 8): v_u_33, (ref 9): v_u_34, (ref 10): v_u_23 ]]
        v_u_9:is_bool(p54)
        v_u_52 = true
        if v_u_53 == true and p54 == false then
            v_u_29 = false
            l_All_0 = v_u_12.PlayerListFilterMode.All
            l_Time_0 = v_u_12.PlayerListOrderMode.Time
        end;
        v_u_53 = p54
        v_u_33 = false
        v_u_34 = 0
        if v_u_53 == true and v_u_23 == false then
            v_u_33 = true
        end;
    end;
    v_u_15.wait_on_next_playerlist_update = function(p55, p56) --[[ Name: wait_on_next_playerlist_update ]] --[[ Line: 215 ]]
        --[[ Upvalues: (ref 1): v_u_25, (copy 2): v_u_28 ]]
        if v_u_25 == -1 then
            v_u_28:push_back(p56)
        else
            p56(p55:get_cached_playerlist_info_list())
        end;
    end;
    v_u_15.get_id_to_playerstatus_dict = function(_) --[[ Name: get_id_to_playerstatus_dict ]] --[[ Line: 224 ]]
        --[[ Upvalues: (copy 1): v_u_16 ]]
        return v_u_16;
    end;
    v_u_15.contains_status_for_id = function(_, p57) --[[ Name: contains_status_for_id ]] --[[ Line: 226 ]]
        --[[ Upvalues: (copy 1): v_u_16 ]]
        return v_u_16:contains(p57);
    end;
    v_u_15.get_status_for_id = function(_, p58) --[[ Name: get_status_for_id ]] --[[ Line: 227 ]]
        --[[ Upvalues: (copy 1): v_u_16, (ref 2): v_u_12 ]]
        if v_u_16:contains(p58) == true then
            return v_u_16:get(p58);
        else
            return v_u_12:new(p58);
        end;
    end;
    v_u_15.update = function(_, p59) --[[ Name: update ]] --[[ Line: 232 ]]
        --[[ Upvalues: (copy 1): v_u_16, (ref 2): v_u_12, (ref 3): v_u_5, (ref 4): v_u_17, (ref 5): v_u_18, (copy 6): v_u_24, (ref 7): v_u_8, (ref 8): v_u_11, (copy 9): v_u_32, (ref 10): v_u_52, (ref 11): v_u_23, (ref 12): v_u_53, (ref 13): v_u_29, (ref 14): v_u_25, (copy 15): p_u_14, (ref 16): v_u_2, (ref 17): v_u_33, (ref 18): v_u_34, (ref 19): v_u_1, (copy 20): v_u_27 ]]
        for _, v60 in v_u_16:key_itr() do
            if v60:get_mode() == v_u_12.Mode.MatchPlaying then
                v60:set_playback_time_sec((v_u_5:IncrementClamp(v60:get_playback_time_sec(), v_u_5:TimescaleToDeltaTime(p59), 0, v60:get_sound_length_sec())))
            end;
        end;
        v_u_17:update(p59)
        if v_u_17:do_flash() then
            v_u_18(v_u_16)
        end;
        for _, v61 in v_u_24:key_itr() do
            if v61:get_activity() == v_u_8.Match then
                v61:set_match_time_ms((math.min(v_u_11:singleton():songkey_get_approx_length_sec(v61:get_song_key()) * 1000, v61:get_match_time_ms() + v_u_5:TimescaleToDeltaTime(p59) * 1000)))
            end;
        end;
        v_u_32:update(p59)
        if v_u_52 == true and v_u_32:is_on_cooldown() ~= true then
            v_u_52 = false
            if v_u_23 ~= v_u_53 then
                local v62 = v_u_23
                v_u_23 = v_u_53
                if v62 == true and v_u_23 == false then
                    v_u_29 = false
                    v_u_24:clear()
                    v_u_25 = -1
                end;
                p_u_14._evt:fire_event_to_server(v_u_2.EVT_Players_ClientSetSubscribePlayerListUpdates, v_u_23)
                v_u_32:add_cooldown(0.75)
            end;
        end;
        if v_u_33 == true then
            v_u_34 = v_u_34 + v_u_5:TimescaleToDeltaTime(p59)
        end;
        if v_u_33 == true and (v_u_23 == true and (v_u_34 > 3.5 and v_u_32:is_on_cooldown() ~= true)) then
            v_u_34 = 0
            p_u_14._evt:fire_event_to_server(v_u_2.EVT_Players_ClientSetSubscribePlayerListUpdates, v_u_23)
            v_u_32:add_cooldown(0.75)
            v_u_1:warnf("playerlist just subscribed but not received EVT_Players_ClientSetSubscribePlayerListUpdates, resend")
        end;
        v_u_27:update(p59)
    end;
    v_u_15.log_debug_info = function(_) --[[ Name: log_debug_info ]] --[[ Line: 301 ]]
        --[[ Upvalues: (ref 1): v_u_1, (copy 2): v_u_16, (ref 3): v_u_6, (ref 4): v_u_12 ]]
        v_u_1:warnf("LocalPlayerStatusManager:log_debug_info")
        for v63, v64 in v_u_16:key_itr() do
            v_u_1:warnf("\tID[%d] Status[%d](%s)", v63, v64:get_mode(), v_u_6:enum_val_to_name(v64:get_mode(), v_u_12.Mode))
        end;
    end;
    v_u_15.get_playerstatus_count = function(_) --[[ Name: get_playerstatus_count ]] --[[ Line: 308 ]]
        --[[ Upvalues: (copy 1): v_u_16 ]]
        return v_u_16:count();
    end;
    f_cons()
    return v_u_15;
end;
return v13;
