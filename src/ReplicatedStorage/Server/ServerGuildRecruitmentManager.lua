-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:18 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_5 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_6 = require(game.ReplicatedStorage.Shared.GuildData)
local v_u_7 = require(game.ReplicatedStorage.Shared.GuildUtil)
require(game.ReplicatedStorage.SPChat.Shared.SPChatMessage)
local v_u_8 = require(game.ReplicatedStorage.Shared.CooldownDelay)
local v_u_9 = require(game.ReplicatedStorage.Shared.APICooldown)
return {
    ["new"] = function(_, p_u_10) --[[ Name: new ]] --[[ Line: 15 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_4, (copy 3): v_u_3, (copy 4): v_u_2, (copy 5): v_u_6, (copy 6): v_u_7, (copy 7): v_u_9, (copy 8): v_u_5, (copy 9): v_u_8 ]]
        local v11 = {}
        local v_u_12 = v_u_1:new()
        local function _(p13) --[[ Name: get_guildid_requesting_join_playerids_set ]] --[[ Line: 19 ]]
            --[[ Upvalues: (copy 1): v_u_12, (ref 2): v_u_1 ]]
            if v_u_12:contains(p13) ~= true then
                v_u_12:add(p13, v_u_1:new())
            end;
            return v_u_12:get(p13);
        end;
        local function _(p14) --[[ Name: remove_all_requests_for_playerid ]] --[[ Line: 26 ]]
            --[[ Upvalues: (copy 1): v_u_12 ]]
            for _, v15 in v_u_12:key_itr() do
                v15:remove(p14)
            end;
        end;
        v11.start = function(_) --[[ Name: start ]] --[[ Line: 32 ]]
            --[[ Upvalues: (copy 1): p_u_10, (ref 2): v_u_4, (ref 3): v_u_3, (ref 4): v_u_2, (ref 5): v_u_6, (ref 6): v_u_7, (ref 7): v_u_1, (copy 8): v_u_12, (ref 9): v_u_9, (ref 10): v_u_5 ]]
            p_u_10._evt:wait_on_event(v_u_4.EVT_GuildRecruitment_GetRecruitmentData_Client, function(p_u_16) --[[ Line: 33 ]]
                --[[ Upvalues: (ref 1): p_u_10, (ref 2): v_u_4, (ref 3): v_u_3, (ref 4): v_u_2, (ref 5): v_u_6, (ref 6): v_u_7, (ref 7): v_u_1, (ref 8): v_u_12 ]]
                local function f_response(p17, p18, p19, p20) --[[ Name: response ]] --[[ Line: 34 ]]
                    --[[ Upvalues: (ref 1): p_u_10, (ref 2): v_u_4, (copy 3): p_u_16 ]]
                    p_u_10._evt:fire_event_to_client(v_u_4.EVT_GuildRecruitment_GetRecruitmentData_ServerResponse, p_u_16, p17, p18, p19, p20)
                end;
                if p_u_10._guild_manager:is_player_in_guild((v_u_3:get_player_id(p_u_16))) == true then
                    return f_response(false, "You are already in a team");
                end;
                p_u_10._guild_manager:get_online_player_guild_data_list(function(p21) --[[ Line: 48 ]]
                    --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_6, (ref 3): v_u_7, (ref 4): v_u_1, (ref 5): v_u_12, (copy 6): p_u_16, (ref 7): p_u_10, (ref 8): v_u_4 ]]
                    local v22 = v_u_2:new()
                    for _, v23 in p21:key_itr() do
                        if v23:get_recruitment_state() ~= v_u_6.RecruitmentState.NotRecruiting and (v23:get_total_members() < v_u_7:get_max_guild_players() and v23:get_total_members() > 0) then
                            v22:push_back(v23:to_table())
                        end;
                    end;
                    local v24 = v_u_1:new()
                    for v25, v26 in v_u_12:key_itr() do
                        if v26:contains(p_u_16.UserId) then
                            v24:add_set(v25)
                        end;
                    end;
                    p_u_10._evt:fire_event_to_client(v_u_4.EVT_GuildRecruitment_GetRecruitmentData_ServerResponse, p_u_16, true, "", v22:get_table(), (v24:key_list():get_table()))
                end)
            end)
            p_u_10._evt:wait_on_event(v_u_4.EVT_GuildRecruitment_AddRecruitmentRequest_Client, function(p_u_27, p_u_28) --[[ Line: 70 ]]
                --[[ Upvalues: (ref 1): p_u_10, (ref 2): v_u_4, (ref 3): v_u_12, (ref 4): v_u_1, (ref 5): v_u_3, (ref 6): v_u_6 ]]
                local function f_response(p29, p30, p31) --[[ Name: response ]] --[[ Line: 71 ]]
                    --[[ Upvalues: (ref 1): p_u_10, (ref 2): v_u_4, (copy 3): p_u_27 ]]
                    if p31 == nil then
                        p31 = false
                    end;
                    p_u_10._evt:fire_event_to_client(v_u_4.EVT_GuildRecruitment_AddRecruitmentRequest_ServerResponse, p_u_27, p29, p30, p31)
                end;
                local function _(p32, p33) --[[ Name: is_player_request_sent ]] --[[ Line: 75 ]]
                    --[[ Upvalues: (ref 1): v_u_12, (ref 2): v_u_1 ]]
                    local v34 = p32:get_guildid()
                    if v_u_12:contains(v34) ~= true then
                        v_u_12:add(v34, v_u_1:new())
                    end;
                    return v_u_12:get(v34):contains(p33);
                end;
                local v_u_35 = v_u_3:get_player_id(p_u_27)
                local v36, _ = p_u_10._guild_manager:is_player_in_guild(v_u_35)
                if v36 == true then
                    return f_response(false, "You are already in a team.");
                end;
                p_u_10._guild_manager:get_guild_data(p_u_28, function(p37) --[[ Line: 82 ]]
                    --[[ Upvalues: (copy 1): v_u_35, (ref 2): v_u_12, (ref 3): v_u_1, (copy 4): f_response, (ref 5): v_u_6, (ref 6): p_u_10, (copy 7): p_u_27, (copy 8): p_u_28, (ref 9): v_u_4 ]]
                    local v38 = v_u_35
                    local v39 = p37:get_guildid()
                    if v_u_12:contains(v39) ~= true then
                        v_u_12:add(v39, v_u_1:new())
                    end;
                    if v_u_12:get(v39):contains(v38) then
                        return f_response(false, "You have already sent a request to this team.");
                    elseif p37:get_recruitment_state() == v_u_6.RecruitmentState.RecruitingAutoAccept then
                        p_u_10._guild_manager:add_player_to_guildid(p_u_27, p_u_28, function(p40, p41) --[[ Line: 86 ]]
                            --[[ Upvalues: (ref 1): p_u_10, (ref 2): v_u_4, (ref 3): p_u_27, (ref 4): p_u_28 ]]
                            local v42 = true
                            if v42 == nil then
                                v42 = false
                            end;
                            p_u_10._evt:fire_event_to_client(v_u_4.EVT_GuildRecruitment_AddRecruitmentRequest_ServerResponse, p_u_27, p40, p41, v42)
                            if p40 then
                                p_u_10._evt:fire_event_to_client(v_u_4.EVT_GuildRecruitment_AcceptInvite_ServerResponse, p_u_27, p40, p41, p_u_28)
                                p_u_10._guild_manager:player_write_guild_message_text(p_u_27, string.format("%s joined the team.", p_u_27.Name))
                            end;
                        end)
                        local l_UserId_0 = p_u_27.UserId
                        for _, v43 in v_u_12:key_itr() do
                            v43:remove(l_UserId_0)
                        end;
                        return;
                    elseif p37:get_recruitment_state() == v_u_6.RecruitmentState.RecruitingMustApprove then
                        local v44 = p_u_28
                        if v_u_12:contains(v44) ~= true then
                            v_u_12:add(v44, v_u_1:new())
                        end;
                        v_u_12:get(v44):add_set(v_u_35)
                        local v45 = nil
                        if v45 == nil then
                            v45 = false
                        end;
                        p_u_10._evt:fire_event_to_client(v_u_4.EVT_GuildRecruitment_AddRecruitmentRequest_ServerResponse, p_u_27, true, "Your request has been sent.", v45)
                        p_u_10._guild_manager:send_guild_data_admins_on_server_message(p37, string.format("Player \"%s\" has requested to join your team. Approve this request in the team menu under team actions.", p_u_27.Name))
                    else
                        local v46 = nil
                        if v46 == nil then
                            v46 = false
                        end;
                        p_u_10._evt:fire_event_to_client(v_u_4.EVT_GuildRecruitment_AddRecruitmentRequest_ServerResponse, p_u_27, false, "This team is not recruiting.", v46)
                    end;
                end)
            end)
            p_u_10._evt:wait_on_event(v_u_4.EVT_GuildRecruitment_GetAdminRecruitmentData_Client, function(p_u_47) --[[ Line: 111 ]]
                --[[ Upvalues: (ref 1): p_u_10, (ref 2): v_u_4, (ref 3): v_u_3, (ref 4): v_u_6, (ref 5): v_u_12, (ref 6): v_u_1 ]]
                local function f_response(p48, p49, p50) --[[ Name: response ]] --[[ Line: 112 ]]
                    --[[ Upvalues: (ref 1): p_u_10, (ref 2): v_u_4, (copy 3): p_u_47 ]]
                    p_u_10._evt:fire_event_to_client(v_u_4.EVT_GuildRecruitment_GetAdminRecruitmentData_ServerResponse, p_u_47, p48, p49, p50)
                end;
                local v_u_51 = v_u_3:get_player_id(p_u_47)
                local v52, v_u_53 = p_u_10._guild_manager:is_player_in_guild(v_u_51)
                if v52 ~= true then
                    return f_response(false, "You are not in the guild", nil);
                end;
                p_u_10._guild_manager:get_guild_data(v_u_53, function(p54) --[[ Line: 119 ]]
                    --[[ Upvalues: (ref 1): v_u_6, (copy 2): v_u_51, (copy 3): f_response, (copy 4): v_u_53, (ref 5): v_u_12, (ref 6): v_u_1, (ref 7): p_u_10, (ref 8): v_u_4, (copy 9): p_u_47 ]]
                    if v_u_6:player_has_admin_access(p54, v_u_51) ~= true then
                        return f_response(false, "You do not have admin rank for this team");
                    end;
                    if p54:get_recruitment_state() ~= v_u_6.RecruitmentState.RecruitingMustApprove then
                        return f_response(false, "Guild recruitment state invalid", nil);
                    end;
                    local v55 = v_u_53
                    if v_u_12:contains(v55) ~= true then
                        v_u_12:add(v55, v_u_1:new())
                    end;
                    p_u_10._evt:fire_event_to_client(v_u_4.EVT_GuildRecruitment_GetAdminRecruitmentData_ServerResponse, p_u_47, true, "", (v_u_12:get(v55):key_list():get_table()))
                end)
            end)
            p_u_10._evt:wait_on_event(v_u_4.EVT_GuildRecruitment_ApprovePlayerToGuild_Client, function(p_u_56, p_u_57) --[[ Line: 128 ]]
                --[[ Upvalues: (ref 1): p_u_10, (ref 2): v_u_4, (ref 3): v_u_3, (ref 4): v_u_6, (ref 5): v_u_12, (ref 6): v_u_1 ]]
                local function f_response(p58, p59) --[[ Name: response ]] --[[ Line: 129 ]]
                    --[[ Upvalues: (ref 1): p_u_10, (ref 2): v_u_4, (copy 3): p_u_56 ]]
                    p_u_10._evt:fire_event_to_client(v_u_4.EVT_GuildRecruitment_ApprovePlayerToGuild_ServerResponse, p_u_56, p58, p59)
                end;
                local v_u_60 = v_u_3:get_player_id(p_u_56)
                local v61, v_u_62 = p_u_10._guild_manager:is_player_in_guild(v_u_60)
                if v61 ~= true then
                    return f_response(false, "You are not in a team");
                end;
                p_u_10._guild_manager:get_guild_data(v_u_62, function(p63) --[[ Line: 136 ]]
                    --[[ Upvalues: (ref 1): v_u_6, (copy 2): v_u_60, (copy 3): f_response, (copy 4): v_u_62, (ref 5): v_u_12, (ref 6): v_u_1, (copy 7): p_u_57, (ref 8): p_u_10, (ref 9): v_u_4, (copy 10): p_u_56 ]]
                    if v_u_6:player_has_admin_access(p63, v_u_60) ~= true then
                        return f_response(false, "You do not have admin rank for this team.");
                    end;
                    if p63:get_recruitment_state() ~= v_u_6.RecruitmentState.RecruitingMustApprove then
                        return f_response(false, "Team recruitment state invalid.");
                    end;
                    local v64 = v_u_62
                    if v_u_12:contains(v64) ~= true then
                        v_u_12:add(v64, v_u_1:new())
                    end;
                    if v_u_12:get(v64):contains(p_u_57) ~= true then
                        return f_response(false, "Recruitment request not found.");
                    end;
                    local v65 = v_u_62
                    if v_u_12:contains(v65) ~= true then
                        v_u_12:add(v65, v_u_1:new())
                    end;
                    v_u_12:get(v65):remove(p_u_57)
                    local v66, _ = p_u_10._guild_manager:is_player_in_guild(p_u_57)
                    if v66 ~= false then
                        return f_response(false, "Target player is already in a team.");
                    end;
                    local v_u_67 = p_u_10._player_manager:id_to_player(p_u_57)
                    if v_u_67 == nil then
                        return f_response(false, "Target player is not in server.");
                    end;
                    p_u_10._guild_manager:add_player_to_guildid(v_u_67, v_u_62, function(p68, p69) --[[ Line: 156 ]]
                        --[[ Upvalues: (ref 1): p_u_10, (ref 2): v_u_4, (copy 3): v_u_67, (ref 4): v_u_62, (ref 5): p_u_56 ]]
                        if p68 then
                            p_u_10._evt:fire_event_to_client(v_u_4.EVT_GuildRecruitment_AcceptInvite_ServerResponse, v_u_67, p68, p69, v_u_62)
                            p_u_10._evt:fire_event_to_client(v_u_4.EVT_GuildRecruitment_ApprovePlayerToGuild_ServerResponse, p_u_56, true, (string.format("%s was added to the team!", v_u_67.Name)))
                            p_u_10._guild_manager:player_write_guild_message_text(p_u_56, string.format("%s approved %s\'s request to join the team.", p_u_56.Name, v_u_67.Name))
                        else
                            p_u_10._evt:fire_event_to_client(v_u_4.EVT_GuildRecruitment_ApprovePlayerToGuild_ServerResponse, p_u_56, p68, p69)
                        end;
                    end)
                    local l_UserId_1 = p_u_56.UserId
                    for _, v70 in v_u_12:key_itr() do
                        v70:remove(l_UserId_1)
                    end;
                end)
            end)
            local v_u_71 = v_u_9:new()
            p_u_10._evt:wait_on_event(v_u_4.EVT_GuildRecruitment_ChangeState_Client, function(p_u_72, p_u_73) --[[ Line: 174 ]]
                --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_6, (copy 3): v_u_71, (ref 4): v_u_3, (ref 5): p_u_10, (ref 6): v_u_4, (ref 7): v_u_12, (ref 8): v_u_1 ]]
                v_u_5:is_enum_member(p_u_73, v_u_6.RecruitmentState)
                v_u_71:queue_key_request(p_u_72.UserId, function() --[[ Line: 176 ]]
                    --[[ Upvalues: (ref 1): v_u_3, (copy 2): p_u_72, (ref 3): p_u_10, (ref 4): v_u_4, (ref 5): v_u_6, (copy 6): p_u_73, (ref 7): v_u_12, (ref 8): v_u_1 ]]
                    local v_u_74 = v_u_3:get_player_id(p_u_72)
                    local function f_response(p75, p76, p77) --[[ Name: response ]] --[[ Line: 178 ]]
                        --[[ Upvalues: (ref 1): p_u_10, (ref 2): v_u_4, (ref 3): p_u_72 ]]
                        p_u_10._evt:fire_event_to_client(v_u_4.EVT_GuildRecruitment_ChangeState_ServerResponse, p_u_72, p75, p76, p77)
                    end;
                    local v78, v_u_79 = p_u_10._guild_manager:is_player_in_guild(v_u_74)
                    if v78 ~= true then
                        return f_response(false, "Player not in team");
                    end;
                    p_u_10._guild_manager:get_guild_data(v_u_79, function(p80) --[[ Line: 185 ]]
                        --[[ Upvalues: (ref 1): v_u_6, (copy 2): v_u_74, (copy 3): f_response, (ref 4): p_u_10, (copy 5): v_u_79, (ref 6): p_u_73, (ref 7): v_u_12, (ref 8): v_u_1, (ref 9): v_u_4, (ref 10): p_u_72 ]]
                        if v_u_6:player_has_admin_access(p80, v_u_74) ~= true then
                            return f_response(false, "You do not have admin rank for this team");
                        end;
                        p_u_10._guild_manager:get_guild_datastore_manager():dsapi_change_guild_recruitment_state(v_u_79, p_u_73, function(p81, p82) --[[ Line: 187 ]]
                            --[[ Upvalues: (ref 1): p_u_10, (ref 2): v_u_79, (ref 3): f_response, (ref 4): v_u_12, (ref 5): v_u_1, (ref 6): v_u_4, (ref 7): p_u_72, (ref 8): v_u_6, (ref 9): p_u_73 ]]
                            if p81 ~= true then
                                p_u_10._guild_manager:clear_guildid_cache(v_u_79)
                                return f_response(false, "Backend error(1)");
                            end;
                            p_u_10._guild_manager:validate_web_table_to_guild_data_cache(v_u_79, p82)
                            local v83 = v_u_79
                            if v_u_12:contains(v83) ~= true then
                                v_u_12:add(v83, v_u_1:new())
                            end;
                            v_u_12:get(v83):clear()
                            p_u_10._evt:fire_event_to_client(v_u_4.EVT_GuildRecruitment_ChangeState_ServerResponse, p_u_72, true, "", p82)
                            p_u_10._guild_manager:player_write_guild_message_text(p_u_72, string.format("%s changed the recruitment status of the team to %s.", p_u_72.Name, v_u_6:get_recruitment_state_name(p_u_73)))
                        end)
                    end)
                end)
            end)
        end;
        v11.player_disconnecting = function(_, p84) --[[ Name: player_disconnecting ]] --[[ Line: 203 ]]
            --[[ Upvalues: (copy 1): v_u_12 ]]
            for _, v85 in v_u_12:key_itr() do
                v85:remove(p84)
            end;
        end;
        local function f_get_guild_data_online_players_count(p86) --[[ Name: get_guild_data_online_players_count ]] --[[ Line: 207 ]]
            --[[ Upvalues: (ref 1): v_u_3 ]]
            local v87 = 0
            for _, v88 in p86:get_member_infos():key_itr() do
                if v_u_3:player_id_online(v88:get_rbxid()) then
                    v87 = v87 + 1
                end;
            end;
            return v87;
        end;
        local v_u_89 = v_u_8:new()
        v11.update = function(_, p90) --[[ Name: update ]] --[[ Line: 220 ]]
            --[[ Upvalues: (copy 1): v_u_89, (copy 2): v_u_12, (copy 3): p_u_10, (copy 4): f_get_guild_data_online_players_count ]]
            v_u_89:update(p90)
            if v_u_89:is_on_cooldown() ~= true then
                v_u_89:add_cooldown(15)
                for v_u_91, _ in v_u_12:key_itr() do
                    p_u_10._guild_manager:get_guild_data(v_u_91, function(p92) --[[ Line: 225 ]]
                        --[[ Upvalues: (ref 1): f_get_guild_data_online_players_count, (ref 2): v_u_12, (copy 3): v_u_91 ]]
                        if f_get_guild_data_online_players_count(p92) <= 0 then
                            v_u_12:remove(v_u_91)
                        end;
                    end)
                end;
            end;
        end;
        v11.get_debug_str = function(_) --[[ Name: get_debug_str ]] --[[ Line: 234 ]]
            --[[ Upvalues: (copy 1): v_u_12 ]]
            local v93 = 0
            for _, v94 in v_u_12:key_itr() do
                v93 = v93 + v94:count()
            end;
            return string.format("Guilds(%d) Requests(%d)", v_u_12:count(), v93);
        end;
        return v11;
    end
};
