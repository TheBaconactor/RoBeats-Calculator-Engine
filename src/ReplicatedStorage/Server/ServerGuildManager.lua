-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:17 PM
-- Time elapsed: 28 milliseconds

local v_u_1 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPMultiDict)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_5 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_6 = require(game.ReplicatedStorage.Shared.GuildUtil)
local v_u_7 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_8 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_9 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_10 = require(game.ReplicatedStorage.Shared.GuildData)
local v_u_11 = require(game.ReplicatedStorage.Shared.GuildRank)
local v_u_12 = require(game.ReplicatedStorage.Shared.CooldownDelay)
local v_u_13 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_14 = require(game.ReplicatedStorage.SPChat.Shared.SPChatMessage)
local v_u_15 = require(game.ReplicatedStorage.Shared.Constants)
local v_u_16 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_17 = require(game.ReplicatedStorage.Avatar.ElementalColor)
local v_u_18 = require(game.ReplicatedStorage.Shared.QueueSequential)
local v_u_19 = require(game.ReplicatedStorage.PlayerInfo.TitleDatabase)
local v_u_20 = require(game.ReplicatedStorage.Shared.GuildBonusUtil)
local v_u_21 = require(game.ReplicatedStorage.Shared.WaitForFinish)
local v_u_22 = require(game.ReplicatedStorage.Server.ServerGuildRecruitmentManager)
local v_u_23 = require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
local v_u_24 = require(game.ReplicatedStorage.Server.ServerAPIManager)
local v_u_25 = require(game.ReplicatedStorage.Shared.GuildMessage)
local v_u_26 = require(game.ReplicatedStorage.PlayerInfo.ChallengePassV2.ChallengePassV2Mission)
local v_u_27 = require(game.ReplicatedStorage.Shared.APICooldown)
local v_u_28 = require(game.ReplicatedStorage.Server.ServerDatastoreImpl.ServerGuildDatastoreManager)
local s_TeleportService_0 = game:GetService("TeleportService")
return {
    ["new"] = function(_, p_u_29) --[[ Name: new ]] --[[ Line: 34 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_22, (copy 3): v_u_28, (copy 4): v_u_12, (copy 5): v_u_6, (copy 6): s_TeleportService_0, (copy 7): v_u_7, (copy 8): v_u_13, (copy 9): v_u_3, (copy 10): v_u_8, (copy 11): v_u_4, (copy 12): v_u_5, (copy 13): v_u_27, (copy 14): v_u_10, (copy 15): v_u_9, (copy 16): v_u_19, (copy 17): v_u_11, (copy 18): v_u_15, (copy 19): v_u_14, (copy 20): v_u_17, (copy 21): v_u_24, (copy 22): v_u_23, (copy 23): v_u_20, (copy 24): v_u_25, (copy 25): v_u_26, (copy 26): v_u_18, (copy 27): v_u_2, (copy 28): v_u_21, (copy 29): v_u_16 ]]
        local v30 = {}
        local v_u_31 = v_u_1:new()
        local v_u_32 = v_u_1:new()
        local v_u_33 = v_u_1:new()
        local v_u_34 = v_u_22:new(p_u_29)
        local v_u_35 = v_u_28:new(p_u_29)
        v30.get_guild_datastore_manager = function(_) --[[ Name: get_guild_datastore_manager ]] --[[ Line: 44 ]]
            --[[ Upvalues: (copy 1): v_u_35 ]]
            return v_u_35;
        end;
        local v_u_36 = v_u_1:new()
        local v_u_37 = v_u_1:new()
        local function _(p38, p39) --[[ Name: playerid_guildid_to_invite_key ]] --[[ Line: 48 ]]
            return string.format("GuildInvite_Player(%d)_Guild(%d)", p38, p39);
        end;
        local v_u_40 = v_u_12:new()
        local v_u_41 = v_u_12:new()
        v30.is_player_in_guild = function(_, p42) --[[ Name: is_player_in_guild ]] --[[ Line: 53 ]]
            --[[ Upvalues: (ref 1): v_u_6, (copy 2): v_u_31 ]]
            local v43 = v_u_6:not_in_guild_id()
            local v44
            if v_u_31:contains(p42) then
                v43 = v_u_31:get(p42)
                if v43 == v_u_6:not_in_guild_id() then
                    v44 = false
                else
                    v44 = true
                end;
            else
                v44 = false
            end;
            return v44, v43;
        end;
        local function _(p_u_45) --[[ Name: get_place_id ]] --[[ Line: 63 ]]
            --[[ Upvalues: (ref 1): s_TeleportService_0 ]]
            local v_u_46 = nil
            local v_u_47 = nil
            local v_u_48 = nil
            local v_u_49 = nil
            local v54, _ = pcall(function() --[[ Line: 65 ]]
                --[[ Upvalues: (ref 1): v_u_46, (ref 2): v_u_47, (ref 3): v_u_48, (ref 4): v_u_49, (ref 5): s_TeleportService_0, (copy 6): p_u_45 ]]
                local v50, v51, v52, v53 = s_TeleportService_0:GetPlayerPlaceInstanceAsync(p_u_45)
                v_u_46 = v50
                v_u_47 = v51
                v_u_48 = v52
                v_u_49 = v53
            end)
            if v54 then
                return v_u_48, v_u_49;
            else
                return -1, -1;
            end;
        end;
        v30.start = function(p_u_55) --[[ Name: start ]] --[[ Line: 76 ]]
            --[[ Upvalues: (copy 1): v_u_34, (copy 2): p_u_29, (ref 3): v_u_7, (ref 4): v_u_13, (ref 5): v_u_3, (ref 6): v_u_8, (ref 7): v_u_6, (ref 8): v_u_4, (ref 9): s_TeleportService_0, (ref 10): v_u_1, (ref 11): v_u_5, (ref 12): v_u_27, (ref 13): v_u_10, (ref 14): v_u_9, (copy 15): v_u_35, (ref 16): v_u_19, (copy 17): v_u_31, (copy 18): v_u_40, (ref 19): v_u_11, (copy 20): v_u_41, (copy 21): v_u_37, (ref 22): v_u_15, (ref 23): v_u_14, (ref 24): v_u_17, (ref 25): v_u_24, (ref 26): v_u_23, (ref 27): v_u_20, (ref 28): v_u_25, (ref 29): v_u_26 ]]
            v_u_34:start()
            p_u_29._evt:wait_on_event(v_u_7.EVT_Guild_GetPlayerInfo_Client, function(p_u_56) --[[ Line: 80 ]]
                --[[ Upvalues: (copy 1): p_u_55, (ref 2): v_u_13, (ref 3): v_u_3, (ref 4): p_u_29, (ref 5): v_u_7 ]]
                local v_u_57, v_u_58 = p_u_55:is_player_in_guild(p_u_56.UserId)
                local v_u_59 = {}
                if v_u_57 then
                    p_u_55:get_guild_data(v_u_58, function(p60) --[[ Line: 84 ]]
                        --[[ Upvalues: (ref 1): v_u_13, (ref 2): v_u_3, (ref 3): p_u_29, (ref 4): v_u_7, (copy 5): p_u_56, (copy 6): v_u_57, (copy 7): v_u_58, (copy 8): v_u_59 ]]
                        local v61 = p60:to_table()
                        if v_u_13.DuplicateGuildPlayers then
                            local v62 = v_u_3:new()
                            v62:push_back_from_list(p60:get_member_infos())
                            local v63 = v62:pop_back()
                            for _ = 1, 20 do
                                v62:push_back(v63)
                            end;
                            local v64 = {}
                            for v65 = 1, v62:count() do
                                v64[v65] = v62:get(v65):to_table()
                            end;
                            v61.MemberInfo = v64
                        end;
                        p_u_29._evt:fire_event_to_client(v_u_7.EVT_Guild_GetPlayerInfo_ServerResponse, p_u_56, v_u_57, v_u_58, v_u_59, v61)
                    end)
                else
                    p_u_29._evt:fire_event_to_client(v_u_7.EVT_Guild_GetPlayerInfo_ServerResponse, p_u_56, v_u_57, v_u_58, v_u_59, nil)
                end;
            end)
            p_u_29._evt:wait_on_event(v_u_7.EVT_Guild_GetPlayerStatus_Client, function(p_u_66, p_u_67) --[[ Line: 106 ]]
                --[[ Upvalues: (ref 1): v_u_8, (ref 2): v_u_6, (ref 3): v_u_4, (ref 4): s_TeleportService_0, (ref 5): v_u_1, (ref 6): p_u_29, (ref 7): v_u_7 ]]
                v_u_8:is_int_in_range(#p_u_67, 0, v_u_6:get_max_guild_players() + 5)
                v_u_4:spawn(function() --[[ Line: 109 ]]
                    --[[ Upvalues: (copy 1): p_u_66, (ref 2): s_TeleportService_0, (copy 3): p_u_67, (ref 4): v_u_6, (ref 5): v_u_1, (ref 6): p_u_29, (ref 7): v_u_7, (ref 8): v_u_4 ]]
                    local l_UserId_0 = p_u_66.UserId
                    local v_u_68 = nil
                    local v_u_69 = nil
                    local v_u_70 = nil
                    local v_u_71 = nil
                    local v76, _ = pcall(function() --[[ Line: 65 ]]
                        --[[ Upvalues: (ref 1): v_u_68, (ref 2): v_u_69, (ref 3): v_u_70, (ref 4): v_u_71, (ref 5): s_TeleportService_0, (copy 6): l_UserId_0 ]]
                        local v72, v73, v74, v75 = s_TeleportService_0:GetPlayerPlaceInstanceAsync(l_UserId_0)
                        v_u_68 = v72
                        v_u_69 = v73
                        v_u_70 = v74
                        v_u_71 = v75
                    end)
                    local v77, v78
                    if v76 then
                        v77 = v_u_70
                        v78 = v_u_71
                    else
                        v77 = -1
                        v78 = -1
                    end;
                    for _, v_u_79 in pairs(p_u_67) do
                        local v_u_80 = nil
                        local v_u_81 = nil
                        local v_u_82 = nil
                        local v_u_83 = nil
                        local v88, _ = pcall(function() --[[ Line: 65 ]]
                            --[[ Upvalues: (ref 1): v_u_80, (ref 2): v_u_81, (ref 3): v_u_82, (ref 4): v_u_83, (ref 5): s_TeleportService_0, (copy 6): v_u_79 ]]
                            local v84, v85, v86, v87 = s_TeleportService_0:GetPlayerPlaceInstanceAsync(v_u_79)
                            v_u_80 = v84
                            v_u_81 = v85
                            v_u_82 = v86
                            v_u_83 = v87
                        end)
                        local v89, v90
                        if v88 then
                            v89 = v_u_82
                            v90 = v_u_83
                        else
                            v89 = -1
                            v90 = -1
                        end;
                        local l_Offline_0 = v_u_6.Status.Offline
                        if v77 ~= -1 and (v89 ~= -1 and v77 == v89) then
                            if v78 == v90 then
                                l_Offline_0 = v_u_6.Status.OnlineSameServer
                            else
                                l_Offline_0 = v_u_6.Status.OnlineDifferentServer
                            end;
                        end;
                        local v91 = v_u_1:new()
                        v91:add(v_u_79, l_Offline_0)
                        p_u_29._evt:fire_event_to_client(v_u_7.EVT_Guild_GetPlayerStatus_ServerResponse, p_u_66, v91:get_table())
                        v_u_4:wait(0.25)
                    end;
                end)
            end)
            p_u_29._evt:wait_on_event(v_u_7.EVT_Guild_TeleportPlayer_Client, function(p92, p_u_93) --[[ Line: 133 ]]
                --[[ Upvalues: (ref 1): v_u_8, (ref 2): s_TeleportService_0, (ref 3): v_u_5 ]]
                v_u_8:is_int(p_u_93)
                local l_UserId_1 = p92.UserId
                local v_u_94 = nil
                local v_u_95 = nil
                local v_u_96 = nil
                local v_u_97 = nil
                local v102, _ = pcall(function() --[[ Line: 65 ]]
                    --[[ Upvalues: (ref 1): v_u_94, (ref 2): v_u_95, (ref 3): v_u_96, (ref 4): v_u_97, (ref 5): s_TeleportService_0, (copy 6): l_UserId_1 ]]
                    local v98, v99, v100, v101 = s_TeleportService_0:GetPlayerPlaceInstanceAsync(l_UserId_1)
                    v_u_94 = v98
                    v_u_95 = v99
                    v_u_96 = v100
                    v_u_97 = v101
                end)
                local v103, v104
                if v102 then
                    v103 = v_u_96
                    v104 = v_u_97
                else
                    v103 = -1
                    v104 = -1
                end;
                local v_u_105 = nil
                local v_u_106 = nil
                local v_u_107 = nil
                local v_u_108 = nil
                local v113, _ = pcall(function() --[[ Line: 65 ]]
                    --[[ Upvalues: (ref 1): v_u_105, (ref 2): v_u_106, (ref 3): v_u_107, (ref 4): v_u_108, (ref 5): s_TeleportService_0, (copy 6): p_u_93 ]]
                    local v109, v110, v111, v112 = s_TeleportService_0:GetPlayerPlaceInstanceAsync(p_u_93)
                    v_u_105 = v109
                    v_u_106 = v110
                    v_u_107 = v111
                    v_u_108 = v112
                end)
                local v114, v115
                if v113 then
                    v114 = v_u_107
                    v115 = v_u_108
                else
                    v114 = -1
                    v115 = -1
                end;
                if v103 == -1 or v114 == -1 then
                    v_u_5:warnf("ServerGuildManager:teleport_player fail player(%d,%d) member_placeid(%d, %d)", v103, v104, v114, v115)
                    return;
                elseif v103 == v114 and v104 ~= v115 then
                    s_TeleportService_0:TeleportToPlaceInstance(v114, v115, p92)
                else
                    v_u_5:warnf("ServerGuildManager:teleport_player fail player(%d,%d) member_placeid(%d, %d)", v103, v104, v114, v115)
                end;
            end)
            local v_u_116 = v_u_27:new()
            p_u_29._evt:wait_on_event(v_u_7.EVT_Guild_CreateGuild_Client, function(p_u_117, p_u_118) --[[ Line: 152 ]]
                --[[ Upvalues: (ref 1): v_u_8, (copy 2): v_u_116, (ref 3): v_u_10, (ref 4): v_u_6, (ref 5): p_u_29, (ref 6): v_u_7, (copy 7): p_u_55, (ref 8): v_u_4, (ref 9): v_u_9, (ref 10): v_u_35, (ref 11): v_u_19, (ref 12): v_u_31 ]]
                v_u_8:is_string(p_u_118)
                v_u_116:queue_key_request(p_u_117.UserId, function() --[[ Line: 155 ]]
                    --[[ Upvalues: (ref 1): v_u_10, (ref 2): v_u_6, (ref 3): p_u_29, (ref 4): v_u_7, (copy 5): p_u_117, (ref 6): p_u_55, (copy 7): p_u_118, (ref 8): v_u_4, (ref 9): v_u_9, (ref 10): v_u_35, (ref 11): v_u_19, (ref 12): v_u_31 ]]
                    local function f_response(p119, p120, p121) --[[ Name: response ]] --[[ Line: 156 ]]
                        --[[ Upvalues: (ref 1): v_u_10, (ref 2): v_u_6, (ref 3): p_u_29, (ref 4): v_u_7, (ref 5): p_u_117 ]]
                        if p121 == nil then
                            p121 = v_u_10:new(v_u_6:not_in_guild_id())
                        end;
                        p_u_29._evt:fire_event_to_client(v_u_7.EVT_Guild_CreateGuild_ServerResponse, p_u_117, p119, p120, p121:to_table())
                    end;
                    if p_u_55:is_player_in_guild(p_u_117.UserId) then
                        return f_response(false, "Already in team");
                    end;
                    local v122, v123 = v_u_6:is_name_valid(p_u_118)
                    if v122 ~= true then
                        return f_response(v122, v123);
                    end;
                    v_u_4:spawn(function() --[[ Line: 167 ]]
                        --[[ Upvalues: (ref 1): v_u_4, (ref 2): p_u_118, (ref 3): p_u_117, (ref 4): p_u_29, (copy 5): f_response, (ref 6): v_u_9, (ref 7): v_u_6, (ref 8): v_u_35, (ref 9): v_u_10, (ref 10): v_u_7, (ref 11): v_u_19, (ref 12): v_u_31, (ref 13): p_u_55 ]]
                        local v_u_124 = v_u_4:filter_string(p_u_118, p_u_117, p_u_117)
                        p_u_29._post_fn:enqueue_function(function() --[[ Line: 169 ]]
                            --[[ Upvalues: (ref 1): p_u_118, (copy 2): v_u_124, (ref 3): f_response, (ref 4): p_u_29, (ref 5): p_u_117, (ref 6): v_u_9, (ref 7): v_u_6, (ref 8): v_u_35, (ref 9): v_u_10, (ref 10): v_u_7, (ref 11): v_u_19, (ref 12): v_u_31, (ref 13): p_u_55 ]]
                            if p_u_118 ~= v_u_124 then
                                return f_response(false, string.format("Name did not pass roblox moderation(%s)", v_u_124));
                            end;
                            p_u_29._player_blob_manager:get_verified_cached_blob(p_u_117.UserId, function(p_u_125) --[[ Line: 174 ]]
                                --[[ Upvalues: (ref 1): v_u_9, (ref 2): v_u_6, (ref 3): f_response, (ref 4): v_u_35, (ref 5): p_u_117, (ref 6): p_u_118, (ref 7): v_u_10, (ref 8): p_u_29, (ref 9): v_u_7, (ref 10): v_u_19, (ref 11): v_u_31, (ref 12): p_u_55 ]]
                                local v_u_126 = v_u_9:get_star_currency(p_u_125)
                                if v_u_126 < v_u_6:get_guild_creation_cost() then
                                    return f_response(false, "Not enough currency");
                                end;
                                v_u_35:dsapi_guild_create(p_u_117.UserId, p_u_118, function(p127, p_u_128) --[[ Line: 178 ]]
                                    --[[ Upvalues: (ref 1): v_u_10, (ref 2): v_u_6, (ref 3): p_u_29, (ref 4): v_u_7, (ref 5): p_u_117, (ref 6): v_u_9, (copy 7): p_u_125, (copy 8): v_u_126, (ref 9): v_u_19, (ref 10): v_u_31, (ref 11): p_u_55, (ref 12): p_u_118 ]]
                                    if p127 ~= true then
                                        local v129 = nil
                                        if v129 == nil then
                                            v129 = v_u_10:new(v_u_6:not_in_guild_id())
                                        end;
                                        p_u_29._evt:fire_event_to_client(v_u_7.EVT_Guild_CreateGuild_ServerResponse, p_u_117, false, "Creating team failed - Backend error. Your account was not charged", v129:to_table())
                                    end;
                                    p_u_29._chat:create_channel_for_teamid(p_u_128.GuildId)
                                    p_u_29._chat:add_player_to_channel_for_teamid(p_u_117, p_u_128.GuildId)
                                    v_u_9:set_star_currency(p_u_125, v_u_126 - v_u_6:get_guild_creation_cost())
                                    v_u_9:set_title_id(p_u_125, v_u_19:singleton():get_guild_title_id())
                                    p_u_29._player_blob_manager:enqueue_blob_sync_request(p_u_117.UserId, v_u_9.PlayerBlobRequestType.Write, function(_) --[[ Line: 189 ]]
                                        --[[ Upvalues: (copy 1): p_u_128, (ref 2): v_u_31, (ref 3): p_u_117, (ref 4): p_u_55, (ref 5): v_u_10, (ref 6): v_u_6, (ref 7): p_u_29, (ref 8): v_u_7, (ref 9): p_u_118 ]]
                                        local l_GuildId_0 = p_u_128.GuildId
                                        v_u_31:add(p_u_117.UserId, l_GuildId_0)
                                        local v130 = p_u_55:validate_web_table_to_guild_data_cache(l_GuildId_0, p_u_128)
                                        if v130 == nil then
                                            v130 = v_u_10:new(v_u_6:not_in_guild_id())
                                        end;
                                        p_u_29._evt:fire_event_to_client(v_u_7.EVT_Guild_CreateGuild_ServerResponse, p_u_117, true, "", v130:to_table())
                                        p_u_29._lobby_manager:push_player_info_updated(p_u_117.UserId)
                                        p_u_29._guild_manager:player_write_guild_message_text(p_u_117, string.format("%s created team \"%s\".", p_u_117.Name, p_u_118))
                                    end)
                                end)
                            end)
                        end)
                    end)
                end)
            end)
            local v_u_131 = v_u_27:new()
            p_u_29._evt:wait_on_event(v_u_7.EVT_Guild_UpdateGuildMessage_Client, function(p_u_132, p_u_133) --[[ Line: 212 ]]
                --[[ Upvalues: (ref 1): v_u_8, (copy 2): v_u_131, (ref 3): p_u_29, (ref 4): v_u_7, (copy 5): p_u_55, (ref 6): v_u_10, (ref 7): v_u_40, (ref 8): v_u_6, (ref 9): v_u_4, (ref 10): v_u_35 ]]
                v_u_8:is_string(p_u_133)
                v_u_131:queue_key_request(p_u_132.UserId, function() --[[ Line: 214 ]]
                    --[[ Upvalues: (ref 1): p_u_29, (ref 2): v_u_7, (copy 3): p_u_132, (ref 4): p_u_55, (ref 5): v_u_10, (ref 6): v_u_40, (ref 7): p_u_133, (ref 8): v_u_6, (ref 9): v_u_4, (ref 10): v_u_35 ]]
                    local function f_response(p134, p135, p136) --[[ Name: response ]] --[[ Line: 215 ]]
                        --[[ Upvalues: (ref 1): p_u_29, (ref 2): v_u_7, (ref 3): p_u_132 ]]
                        local v137
                        if p136 then
                            v137 = p136:to_table()
                        else
                            v137 = nil
                        end;
                        p_u_29._evt:fire_event_to_client(v_u_7.EVT_Guild_UpdateGuildMessage_ServerResponse, p_u_132, p134, p135, v137)
                    end;
                    local v138, v_u_139 = p_u_55:is_player_in_guild(p_u_132.UserId)
                    if v138 ~= true then
                        return f_response(false, "Player not in team", nil);
                    end;
                    p_u_55:get_guild_data(v_u_139, function(p_u_140) --[[ Line: 223 ]]
                        --[[ Upvalues: (ref 1): v_u_10, (ref 2): p_u_132, (copy 3): f_response, (ref 4): v_u_40, (ref 5): p_u_133, (ref 6): v_u_6, (ref 7): v_u_4, (ref 8): p_u_29, (ref 9): v_u_35, (copy 10): v_u_139, (ref 11): p_u_55, (ref 12): v_u_7 ]]
                        if v_u_10:player_has_admin_access(p_u_140, p_u_132.UserId) ~= true then
                            return f_response(false, "EVT_Guild_UpdateGuildMessage_Client does not have admin access", nil);
                        end;
                        if v_u_40:is_on_cooldown(p_u_132.UserId) then
                            return f_response(false, "EVT_Guild_UpdateGuildMessage_Client on cooldown", nil);
                        end;
                        p_u_133 = p_u_133:sub(1, v_u_6:guild_message_max_length())
                        v_u_4:spawn(function() --[[ Line: 227 ]]
                            --[[ Upvalues: (ref 1): p_u_133, (ref 2): v_u_4, (ref 3): p_u_132, (ref 4): p_u_29, (ref 5): p_u_140, (ref 6): v_u_40, (ref 7): v_u_35, (ref 8): v_u_139, (ref 9): p_u_55, (ref 10): v_u_7 ]]
                            p_u_133 = v_u_4:filter_string(p_u_133, p_u_132, p_u_132)
                            p_u_29._post_fn:enqueue_function(function() --[[ Line: 229 ]]
                                --[[ Upvalues: (ref 1): p_u_140, (ref 2): p_u_133, (ref 3): v_u_40, (ref 4): p_u_132, (ref 5): v_u_35, (ref 6): v_u_139, (ref 7): p_u_55, (ref 8): p_u_29, (ref 9): v_u_7 ]]
                                p_u_140:set_message(p_u_133)
                                v_u_40:add_cooldown_to_id(p_u_132.UserId, 2)
                                v_u_35:dsapi_guild_update_info(v_u_139, p_u_140, function(p141, p142) --[[ Line: 232 ]]
                                    --[[ Upvalues: (ref 1): p_u_140, (ref 2): p_u_55, (ref 3): v_u_139, (ref 4): p_u_29, (ref 5): v_u_7, (ref 6): p_u_132 ]]
                                    if p141 then
                                        p_u_140 = p_u_55:validate_web_table_to_guild_data_cache(v_u_139, p142)
                                    end;
                                    local v143 = p_u_140
                                    local v144
                                    if v143 then
                                        v144 = v143:to_table()
                                    else
                                        v144 = nil
                                    end;
                                    p_u_29._evt:fire_event_to_client(v_u_7.EVT_Guild_UpdateGuildMessage_ServerResponse, p_u_132, true, "", v144)
                                    p_u_29._guild_manager:player_write_guild_message_text(p_u_132, string.format("%s updated the team message.", p_u_132.Name))
                                end)
                            end)
                        end)
                    end)
                end)
            end)
            local v_u_145 = v_u_27:new()
            p_u_29._evt:wait_on_event(v_u_7.EVT_Guild_UpdateGuildIcon_Client, function(p_u_146, p_u_147) --[[ Line: 251 ]]
                --[[ Upvalues: (ref 1): v_u_8, (copy 2): v_u_145, (ref 3): p_u_29, (ref 4): v_u_7, (copy 5): p_u_55, (ref 6): v_u_10, (ref 7): v_u_40, (ref 8): v_u_6, (ref 9): v_u_35 ]]
                v_u_8:is_string(p_u_147)
                v_u_145:queue_key_request(p_u_146.UserId, function() --[[ Line: 253 ]]
                    --[[ Upvalues: (ref 1): p_u_29, (ref 2): v_u_7, (copy 3): p_u_146, (ref 4): p_u_55, (ref 5): v_u_10, (ref 6): v_u_40, (ref 7): p_u_147, (ref 8): v_u_6, (ref 9): v_u_35 ]]
                    local function f_response(p148, p149, p150) --[[ Name: response ]] --[[ Line: 254 ]]
                        --[[ Upvalues: (ref 1): p_u_29, (ref 2): v_u_7, (ref 3): p_u_146 ]]
                        local v151
                        if p150 then
                            v151 = p150:to_table()
                        else
                            v151 = nil
                        end;
                        p_u_29._evt:fire_event_to_client(v_u_7.EVT_Guild_UpdateGuildIcon_ServerResponse, p_u_146, p148, p149, v151)
                    end;
                    local v152, v_u_153 = p_u_55:is_player_in_guild(p_u_146.UserId)
                    if v152 ~= true then
                        return f_response(false, "Player not in team", nil);
                    end;
                    p_u_55:get_guild_data(v_u_153, function(p_u_154) --[[ Line: 262 ]]
                        --[[ Upvalues: (ref 1): v_u_10, (ref 2): p_u_146, (copy 3): f_response, (ref 4): v_u_40, (ref 5): p_u_147, (ref 6): v_u_6, (ref 7): v_u_35, (copy 8): v_u_153, (ref 9): p_u_55, (ref 10): p_u_29, (ref 11): v_u_7 ]]
                        if v_u_10:player_has_admin_access(p_u_154, p_u_146.UserId) ~= true then
                            return f_response(false, "EVT_Guild_UpdateGuildMessage_Client does not have admin access", nil);
                        end;
                        if v_u_40:is_on_cooldown(p_u_146.UserId) then
                            return f_response(false, "EVT_Guild_UpdateGuildMessage_Client on cooldown", nil);
                        end;
                        p_u_147 = p_u_147:sub(1, v_u_6:guild_name_max_length())
                        p_u_154:set_icon(p_u_147)
                        v_u_40:add_cooldown_to_id(p_u_146.UserId, 2)
                        v_u_35:dsapi_guild_update_info(v_u_153, p_u_154, function(p155, p156) --[[ Line: 268 ]]
                            --[[ Upvalues: (ref 1): p_u_154, (ref 2): p_u_55, (ref 3): v_u_153, (ref 4): p_u_29, (ref 5): v_u_7, (ref 6): p_u_146 ]]
                            if p155 then
                                p_u_154 = p_u_55:validate_web_table_to_guild_data_cache(v_u_153, p156)
                            end;
                            local v157 = p_u_154
                            local v158
                            if v157 then
                                v158 = v157:to_table()
                            else
                                v158 = nil
                            end;
                            p_u_29._evt:fire_event_to_client(v_u_7.EVT_Guild_UpdateGuildIcon_ServerResponse, p_u_146, true, "", v158)
                            p_u_29._guild_manager:player_write_guild_message_text(p_u_146, string.format("%s updated the team icon.", p_u_146.Name))
                        end)
                    end)
                end)
            end)
            local v_u_159 = v_u_27:new()
            p_u_29._evt:wait_on_event(v_u_7.EVT_Guild_EditPlayerRank_Client, function(p_u_160, p_u_161, p_u_162) --[[ Line: 285 ]]
                --[[ Upvalues: (ref 1): v_u_8, (ref 2): v_u_11, (copy 3): v_u_159, (ref 4): p_u_29, (ref 5): v_u_7, (copy 6): p_u_55, (ref 7): v_u_10, (ref 8): v_u_35, (ref 9): v_u_4 ]]
                v_u_8:is_int(p_u_161)
                v_u_8:is_enum_member(p_u_162, v_u_11)
                v_u_159:queue_key_request(p_u_160.UserId, function() --[[ Line: 288 ]]
                    --[[ Upvalues: (ref 1): p_u_29, (ref 2): v_u_7, (copy 3): p_u_160, (copy 4): p_u_161, (ref 5): p_u_55, (ref 6): v_u_10, (ref 7): v_u_11, (copy 8): p_u_162, (ref 9): v_u_35, (ref 10): v_u_4 ]]
                    local function f_response(p163, p164, p165) --[[ Name: response ]] --[[ Line: 289 ]]
                        --[[ Upvalues: (ref 1): p_u_29, (ref 2): v_u_7, (ref 3): p_u_160 ]]
                        local v166
                        if p165 then
                            v166 = p165:to_table()
                        else
                            v166 = nil
                        end;
                        p_u_29._evt:fire_event_to_client(v_u_7.EVT_Guild_EditPlayerRank_ServerResponse, p_u_160, p163, p164, v166)
                    end;
                    if p_u_160.UserId == p_u_161 then
                        return f_response(false, "Cannot set own rank", nil);
                    end;
                    local v167, v_u_168 = p_u_55:is_player_in_guild(p_u_160.UserId)
                    if v167 ~= true then
                        return f_response(false, "Player not in team", nil);
                    end;
                    p_u_55:get_guild_data(v_u_168, function(p_u_169) --[[ Line: 297 ]]
                        --[[ Upvalues: (ref 1): v_u_10, (ref 2): p_u_160, (ref 3): p_u_161, (copy 4): f_response, (ref 5): v_u_11, (ref 6): p_u_162, (ref 7): v_u_35, (copy 8): v_u_168, (ref 9): p_u_55, (ref 10): p_u_29, (ref 11): v_u_7, (ref 12): v_u_4 ]]
                        local v170 = v_u_10:get_player_info(p_u_169, p_u_160.UserId)
                        local v_u_171 = v_u_10:get_player_info(p_u_169, p_u_161)
                        if v170 == nil or v_u_171 == nil then
                            return f_response(false, "Editor or target not found", nil);
                        end;
                        if v_u_11:can_set_rank(v170:get_rank(), v_u_171:get_rank(), p_u_162) ~= true then
                            return f_response(false, "Cannot edit rank of target", nil);
                        end;
                        v_u_35:dsapi_guild_edit_member_rank(v_u_168, p_u_160.UserId, p_u_161, p_u_162, function(p172, p173) --[[ Line: 302 ]]
                            --[[ Upvalues: (ref 1): p_u_169, (ref 2): p_u_55, (ref 3): v_u_168, (ref 4): p_u_29, (ref 5): v_u_7, (ref 6): p_u_160, (copy 7): v_u_171, (ref 8): v_u_4, (ref 9): p_u_162, (ref 10): v_u_11 ]]
                            if p172 then
                                p_u_169 = p_u_55:validate_web_table_to_guild_data_cache(v_u_168, p173)
                            end;
                            local v174 = p_u_169
                            local v175
                            if v174 then
                                v175 = v174:to_table()
                            else
                                v175 = nil
                            end;
                            p_u_29._evt:fire_event_to_client(v_u_7.EVT_Guild_EditPlayerRank_ServerResponse, p_u_160, true, "", v175)
                            p_u_29._guild_manager:player_write_guild_message_text(p_u_160, string.format("%s changed %s\'s rank to \'%s\'.", p_u_160.Name, v_u_171:get_name(), v_u_4:enum_val_to_name(p_u_162, v_u_11)))
                        end)
                    end)
                end)
            end)
            local v_u_176 = v_u_27:new()
            p_u_29._evt:wait_on_event(v_u_7.EVT_Guild_EditGuildName_Client, function(p_u_177, p_u_178) --[[ Line: 319 ]]
                --[[ Upvalues: (ref 1): v_u_8, (copy 2): v_u_176, (ref 3): p_u_29, (ref 4): v_u_7, (copy 5): p_u_55, (ref 6): v_u_10, (ref 7): v_u_6, (ref 8): v_u_4, (ref 9): v_u_35 ]]
                v_u_8:is_string(p_u_178)
                v_u_176:queue_key_request(p_u_177.UserId, function() --[[ Line: 321 ]]
                    --[[ Upvalues: (ref 1): p_u_29, (ref 2): v_u_7, (copy 3): p_u_177, (ref 4): p_u_55, (ref 5): v_u_10, (ref 6): v_u_6, (copy 7): p_u_178, (ref 8): v_u_4, (ref 9): v_u_35 ]]
                    local function f_response(p179, p180, p181) --[[ Name: response ]] --[[ Line: 322 ]]
                        --[[ Upvalues: (ref 1): p_u_29, (ref 2): v_u_7, (ref 3): p_u_177 ]]
                        local v182
                        if p181 then
                            v182 = p181:to_table()
                        else
                            v182 = nil
                        end;
                        p_u_29._evt:fire_event_to_client(v_u_7.EVT_Guild_EditGuildName_ServerResponse, p_u_177, p179, p180, v182)
                    end;
                    local l_UserId_2 = p_u_177.UserId
                    local v183, v_u_184 = p_u_55:is_player_in_guild(p_u_177.UserId)
                    if v183 ~= true then
                        return f_response(false, "Player not in team", nil);
                    end;
                    p_u_55:get_guild_data(v_u_184, function(p_u_185) --[[ Line: 331 ]]
                        --[[ Upvalues: (ref 1): v_u_10, (copy 2): l_UserId_2, (copy 3): f_response, (ref 4): v_u_6, (ref 5): p_u_178, (ref 6): v_u_4, (ref 7): p_u_177, (ref 8): v_u_35, (copy 9): v_u_184, (ref 10): p_u_55, (ref 11): p_u_29, (ref 12): v_u_7 ]]
                        if v_u_10:player_has_admin_access(p_u_185, l_UserId_2) ~= true then
                            return f_response(false, "You do not have admin rank for this team");
                        end;
                        local v186, v187 = v_u_6:is_name_valid(p_u_178)
                        if v186 ~= true then
                            return f_response(v186, v187);
                        end;
                        local v188 = v_u_4:filter_string(p_u_178, p_u_177, p_u_177)
                        if p_u_178 ~= v188 then
                            return f_response(false, string.format("Name did not pass roblox moderation(%s)", v188), p_u_185);
                        end;
                        if p_u_185:get_star_currency() < v_u_6:get_guild_change_name_cost() then
                            return f_response(false, "Not enough currency", p_u_185);
                        end;
                        v_u_35:dsapi_change_guild_name(v_u_184, p_u_178, function(p189, p190) --[[ Line: 345 ]]
                            --[[ Upvalues: (ref 1): p_u_185, (ref 2): p_u_55, (ref 3): v_u_184, (ref 4): p_u_29, (ref 5): v_u_7, (ref 6): p_u_177, (ref 7): p_u_178 ]]
                            if p189 then
                                p_u_185 = p_u_55:validate_web_table_to_guild_data_cache(v_u_184, p190)
                                local v191 = p_u_185
                                local v192
                                if v191 then
                                    v192 = v191:to_table()
                                else
                                    v192 = nil
                                end;
                                p_u_29._evt:fire_event_to_client(v_u_7.EVT_Guild_EditGuildName_ServerResponse, p_u_177, true, "", v192)
                                p_u_29._lobby_manager:push_player_info_updated(p_u_177.UserId)
                                p_u_29._guild_manager:player_write_guild_message_text(p_u_177, string.format("Player \"%s\" changed team name to \"%s\".", p_u_177.Name, p_u_178))
                            else
                                local v193 = p_u_185
                                local v194
                                if v193 then
                                    v194 = v193:to_table()
                                else
                                    v194 = nil
                                end;
                                p_u_29._evt:fire_event_to_client(v_u_7.EVT_Guild_EditGuildName_ServerResponse, p_u_177, false, "Backend Failed", v194)
                            end;
                        end)
                    end)
                end)
            end)
            local v_u_195 = v_u_27:new():set_cooldown(2)
            p_u_29._evt:wait_on_event(v_u_7.EVT_Guild_KickPlayer_Client, function(p_u_196, p_u_197) --[[ Line: 367 ]]
                --[[ Upvalues: (ref 1): v_u_8, (copy 2): v_u_195, (ref 3): p_u_29, (ref 4): v_u_7, (copy 5): p_u_55, (ref 6): v_u_10, (ref 7): v_u_35, (ref 8): v_u_31 ]]
                v_u_8:is_int(p_u_197)
                v_u_195:queue_key_request(p_u_196.UserId, function() --[[ Line: 369 ]]
                    --[[ Upvalues: (ref 1): p_u_29, (ref 2): v_u_7, (copy 3): p_u_196, (ref 4): p_u_55, (ref 5): v_u_10, (copy 6): p_u_197, (ref 7): v_u_35, (ref 8): v_u_31 ]]
                    local function f_response(p198, p199, p200) --[[ Name: response ]] --[[ Line: 370 ]]
                        --[[ Upvalues: (ref 1): p_u_29, (ref 2): v_u_7, (ref 3): p_u_196 ]]
                        local v201
                        if p200 then
                            v201 = p200:to_table()
                        else
                            v201 = nil
                        end;
                        p_u_29._evt:fire_event_to_client(v_u_7.EVT_Guild_KickPlayer_ServerResponse, p_u_196, p198, p199, v201)
                    end;
                    local v202, v_u_203 = p_u_55:is_player_in_guild(p_u_196.UserId)
                    if v202 ~= true then
                        return f_response(false, "Player not in team", nil);
                    end;
                    p_u_55:get_guild_data(v_u_203, function(p_u_204) --[[ Line: 377 ]]
                        --[[ Upvalues: (ref 1): v_u_10, (ref 2): p_u_196, (ref 3): p_u_197, (copy 4): f_response, (ref 5): v_u_35, (copy 6): v_u_203, (ref 7): v_u_31, (ref 8): p_u_29, (ref 9): p_u_55, (ref 10): v_u_7 ]]
                        local v205 = v_u_10:get_player_info(p_u_204, p_u_196.UserId)
                        local v_u_206 = v_u_10:get_player_info(p_u_204, p_u_197)
                        if v205 == nil or v_u_206 == nil then
                            return f_response(false, "Editor or target not found", nil);
                        end;
                        if v_u_10:member_can_kick_member(v205, v_u_206) ~= true then
                            return f_response(false, "Editor does not have permissions to kick", nil);
                        end;
                        v_u_35:dsapi_guild_remove_member(v_u_203, p_u_197, function(p207, p208) --[[ Line: 382 ]]
                            --[[ Upvalues: (ref 1): v_u_31, (ref 2): p_u_197, (ref 3): p_u_29, (ref 4): p_u_196, (ref 5): v_u_203, (ref 6): p_u_204, (ref 7): p_u_55, (copy 8): v_u_206, (ref 9): v_u_7 ]]
                            if p207 then
                                v_u_31:remove(p_u_197)
                                p_u_29._chat:remove_player_from_channel_for_teamid(p_u_196, v_u_203)
                                p_u_204 = p_u_55:validate_web_table_to_guild_data_cache(v_u_203, p208)
                                p_u_29._guild_manager:player_write_guild_message_text(p_u_196, string.format("%s removed %s from the team.", p_u_196.Name, v_u_206:get_name()), v_u_203)
                            end;
                            local v209 = p_u_204
                            local v210
                            if v209 then
                                v210 = v209:to_table()
                            else
                                v210 = nil
                            end;
                            p_u_29._evt:fire_event_to_client(v_u_7.EVT_Guild_KickPlayer_ServerResponse, p_u_196, true, "", v210)
                        end)
                    end)
                end)
            end)
            p_u_29._evt:wait_on_event(v_u_7.EVT_Guild_InvitePlayer_Client, function(p_u_211, p_u_212) --[[ Line: 401 ]]
                --[[ Upvalues: (ref 1): v_u_8, (ref 2): p_u_29, (ref 3): v_u_7, (copy 4): p_u_55, (ref 5): v_u_41, (ref 6): v_u_6, (ref 7): v_u_10, (ref 8): v_u_11, (ref 9): v_u_37, (ref 10): v_u_15, (ref 11): v_u_14, (ref 12): v_u_4 ]]
                v_u_8:is_int(p_u_212)
                local function f_response(p213, p214) --[[ Name: response ]] --[[ Line: 403 ]]
                    --[[ Upvalues: (ref 1): p_u_29, (ref 2): v_u_7, (copy 3): p_u_211 ]]
                    p_u_29._evt:fire_event_to_client(v_u_7.EVT_Guild_InvitePlayer_ServerResponse, p_u_211, p213, p214)
                end;
                if p_u_55:is_player_in_guild(p_u_212) then
                    return f_response(false, "Player already in team");
                end;
                local v_u_215 = p_u_29._player_manager:id_to_player(p_u_212)
                if v_u_215 == nil then
                    return f_response(false, "Player not found");
                end;
                local v216, v_u_217 = p_u_55:is_player_in_guild(p_u_211.UserId)
                if v216 ~= true then
                    return f_response(false, "Player not in team");
                end;
                if v_u_41:is_on_cooldown(p_u_211.UserId) then
                    return f_response(false, "Sending too many team invites, please wait");
                end;
                v_u_41:add_cooldown_to_id(p_u_211.UserId, 2)
                p_u_55:get_guild_data(v_u_217, function(p218) --[[ Line: 417 ]]
                    --[[ Upvalues: (ref 1): v_u_6, (copy 2): f_response, (ref 3): v_u_10, (copy 4): p_u_211, (ref 5): v_u_11, (ref 6): v_u_37, (copy 7): p_u_212, (copy 8): v_u_217, (ref 9): v_u_15, (ref 10): p_u_29, (copy 11): v_u_215, (ref 12): v_u_14, (ref 13): v_u_4, (ref 14): v_u_7 ]]
                    if p218:get_member_infos():count() >= v_u_6:get_max_guild_players() then
                        return f_response(false, "Team is at max number of players");
                    end;
                    local v219 = v_u_10:get_player_info(p218, p_u_211.UserId)
                    if v219 == nil then
                        return f_response(false, "Sender is not in team");
                    end;
                    if v_u_11:can_invite_members(v219:get_rank()) ~= true then
                        return f_response(false, "You do not have permissions to invite members");
                    end;
                    v_u_37:add(string.format("GuildInvite_Player(%d)_Guild(%d)", p_u_212, v_u_217), v_u_15.GUILD_INVITE_PENDING_TIME_SEC)
                    p_u_29._chat:get_chat_service():send_system_message_to_player_for_channel(v_u_215, p_u_29._chat:get_chat_service():get_channel(p_u_29._chat:get_chat_service():get_server_system_channel_id()), string.format("%s has invited you to their Team \'%s\'. Click on this message to join!", p_u_211.Name, p218:get_name()), function(p220) --[[ Line: 428 ]]
                        --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_217, (ref 3): v_u_4 ]]
                        p220:set_extradata(v_u_14.ExtraDataType.GuildInvite, v_u_217)
                        p220:set_icon(v_u_4:important_assetid())
                    end)
                    p_u_29._evt:fire_event_to_client(v_u_7.EVT_Guild_InvitePlayer_ServerResponse, p_u_211, true, "")
                end)
            end)
            p_u_55.add_player_to_guildid = function(p_u_221, p_u_222, p_u_223, p_u_224) --[[ Name: add_player_to_guildid ]] --[[ Line: 437 ]]
                --[[ Upvalues: (ref 1): v_u_8, (ref 2): v_u_6, (ref 3): v_u_35, (ref 4): p_u_29, (ref 5): v_u_31, (ref 6): v_u_9, (ref 7): v_u_19 ]]
                v_u_8:is_int(p_u_223)
                local function f_response(p225, p226) --[[ Name: response ]] --[[ Line: 439 ]]
                    --[[ Upvalues: (copy 1): p_u_224 ]]
                    p_u_224(p225, p226)
                end;
                if p_u_221:is_player_in_guild(p_u_222.UserId) then
                    return f_response(false, "Failed: Already in team.");
                end;
                p_u_221:get_guild_data(p_u_223, function(p_u_227) --[[ Line: 444 ]]
                    --[[ Upvalues: (ref 1): v_u_6, (copy 2): p_u_223, (copy 3): f_response, (ref 4): v_u_35, (copy 5): p_u_222, (ref 6): p_u_29, (ref 7): v_u_31, (copy 8): p_u_221, (ref 9): v_u_9, (ref 10): v_u_19, (copy 11): p_u_224 ]]
                    if p_u_227:get_guildid() == v_u_6:not_in_guild_id() or p_u_223 ~= p_u_227:get_guildid() then
                        return f_response(false, "Failed: Invalid Guild");
                    end;
                    if p_u_227:get_member_infos():count() >= v_u_6:get_max_guild_players() then
                        return f_response(false, "Failed: Team is at max number of players");
                    end;
                    v_u_35:dsapi_guild_add_member(p_u_223, p_u_222.UserId, function(p228, p_u_229) --[[ Line: 448 ]]
                        --[[ Upvalues: (ref 1): p_u_29, (ref 2): p_u_222, (ref 3): v_u_31, (ref 4): p_u_227, (ref 5): p_u_223, (ref 6): p_u_221, (ref 7): v_u_9, (ref 8): v_u_19, (ref 9): p_u_224 ]]
                        if p228 then
                            p_u_29._player_blob_manager:get_verified_cached_blob(p_u_222.UserId, function(p230) --[[ Line: 450 ]]
                                --[[ Upvalues: (ref 1): v_u_31, (ref 2): p_u_222, (ref 3): p_u_227, (ref 4): p_u_29, (ref 5): p_u_223, (ref 6): p_u_221, (copy 7): p_u_229, (ref 8): v_u_9, (ref 9): v_u_19, (ref 10): p_u_224 ]]
                                v_u_31:add(p_u_222.UserId, p_u_227:get_guildid())
                                p_u_29._chat:create_channel_for_teamid(p_u_223)
                                p_u_29._chat:add_player_to_channel_for_teamid(p_u_222, p_u_223)
                                p_u_227 = p_u_221:validate_web_table_to_guild_data_cache(p_u_223, p_u_229)
                                v_u_9:set_title_id(p230, v_u_19:singleton():get_guild_title_id())
                                p_u_29._player_blob_manager:enqueue_blob_sync_request(p_u_222.UserId, v_u_9.PlayerBlobRequestType.Write, function(_) --[[ Line: 459 ]]
                                    --[[ Upvalues: (ref 1): p_u_227, (ref 2): p_u_224, (ref 3): p_u_29, (ref 4): p_u_222 ]]
                                    p_u_224(true, (string.format("Joined team \'%s\'!", p_u_227:get_name())))
                                    p_u_29._lobby_manager:push_player_info_updated(p_u_222.UserId)
                                end)
                                p_u_221:send_guild_data_admins_on_server_message(p_u_227, string.format("Player \"%s\" has joined the team!", p_u_222.Name))
                            end)
                        else
                            p_u_224(false, "Could not add player to team (backend).")
                        end;
                    end)
                end)
            end;
            p_u_55.send_guild_data_admins_on_server_message = function(_, p231, p232) --[[ Name: send_guild_data_admins_on_server_message ]] --[[ Line: 476 ]]
                --[[ Upvalues: (ref 1): v_u_10, (ref 2): p_u_29, (ref 3): v_u_4 ]]
                for _, v233 in p231:get_member_infos():key_itr() do
                    if v_u_10:player_has_admin_access(p231, v233:get_rbxid()) then
                        local v234 = p_u_29._player_manager:id_to_player(v233:get_rbxid())
                        if v234 then
                            p_u_29._chat:get_chat_service():send_system_message_to_player_for_channel(v234, p_u_29._chat:get_chat_service():get_channel(p_u_29._chat:get_chat_service():get_server_system_channel_id()), p232, function(p235) --[[ Line: 485 ]]
                                --[[ Upvalues: (ref 1): v_u_4 ]]
                                p235:set_icon(v_u_4:important_assetid())
                            end)
                        end;
                    end;
                end;
            end;
            p_u_29._evt:wait_on_event(v_u_7.EVT_Guild_AcceptInvite_Client, function(p_u_236, p237) --[[ Line: 494 ]]
                --[[ Upvalues: (ref 1): v_u_8, (ref 2): p_u_29, (ref 3): v_u_7, (ref 4): v_u_37, (copy 5): p_u_55 ]]
                v_u_8:is_int(p237)
                local function f_response(p238, p239) --[[ Name: response ]] --[[ Line: 496 ]]
                    --[[ Upvalues: (ref 1): p_u_29, (ref 2): v_u_7, (copy 3): p_u_236 ]]
                    p_u_29._evt:fire_event_to_client(v_u_7.EVT_Guild_AcceptInvite_ServerResponse, p_u_236, p238, p239)
                end;
                local v240 = string.format("GuildInvite_Player(%d)_Guild(%d)", p_u_236.UserId, p237)
                if v_u_37:contains(v240) ~= true then
                    return f_response(false, "Failed: Invite has expired");
                end;
                v_u_37:remove(v240)
                p_u_55:add_player_to_guildid(p_u_236, p237, function(p241, p242) --[[ Line: 504 ]]
                    --[[ Upvalues: (ref 1): p_u_29, (ref 2): v_u_7, (copy 3): p_u_236 ]]
                    p_u_29._evt:fire_event_to_client(v_u_7.EVT_Guild_AcceptInvite_ServerResponse, p_u_236, p241, p242)
                    p_u_29._guild_manager:player_write_guild_message_text(p_u_236, string.format("%s accepted an invite to the team.", p_u_236.Name))
                end)
            end)
            local v_u_243 = v_u_27:new()
            p_u_29._evt:wait_on_event(v_u_7.EVT_Guild_DonateStars_Client, function(p_u_244, p_u_245) --[[ Line: 515 ]]
                --[[ Upvalues: (ref 1): v_u_8, (ref 2): v_u_4, (copy 3): v_u_243, (ref 4): p_u_29, (ref 5): v_u_7, (ref 6): v_u_9, (copy 7): p_u_55, (ref 8): v_u_35, (ref 9): v_u_6 ]]
                v_u_8:is_int_greater_than(p_u_245, 0)
                v_u_8:is_true(v_u_4:is_finite(p_u_245))
                v_u_8:is_true(p_u_245 < v_u_4:large_number())
                v_u_243:queue_key_request(p_u_244.UserId, function() --[[ Line: 520 ]]
                    --[[ Upvalues: (ref 1): v_u_4, (copy 2): p_u_244, (ref 3): p_u_29, (ref 4): v_u_7, (copy 5): p_u_245, (ref 6): v_u_9, (ref 7): p_u_55, (ref 8): v_u_35, (ref 9): v_u_6 ]]
                    local v_u_246 = v_u_4:get_player_id(p_u_244)
                    local function f_response(p247, p248, p249) --[[ Name: response ]] --[[ Line: 522 ]]
                        --[[ Upvalues: (ref 1): p_u_29, (ref 2): v_u_7, (ref 3): p_u_244 ]]
                        p_u_29._evt:fire_event_to_client(v_u_7.EVT_Guild_DonateStars_ServerResponse, p_u_244, p247, p248, p249)
                    end;
                    if p_u_245 == 0 then
                        return f_response(false, "Cannot donate zero stars", nil);
                    end;
                    p_u_29._player_blob_manager:get_verified_cached_blob(v_u_246, function(p250) --[[ Line: 526 ]]
                        --[[ Upvalues: (ref 1): v_u_9, (ref 2): p_u_245, (copy 3): f_response, (ref 4): p_u_55, (ref 5): p_u_244, (ref 6): p_u_29, (copy 7): v_u_246, (ref 8): v_u_35, (ref 9): v_u_7, (ref 10): v_u_6 ]]
                        if v_u_9:get_star_currency(p250) - p_u_245 < 0 then
                            return f_response(false, "Not enough stars", nil);
                        end;
                        local v251, v_u_252 = p_u_55:is_player_in_guild(p_u_244.UserId)
                        if v251 ~= true then
                            return f_response(false, "Player not in team", nil);
                        end;
                        v_u_9:set_star_currency(p250, v_u_9:get_star_currency(p250) - p_u_245)
                        p_u_29._player_blob_manager:enqueue_blob_sync_request(v_u_246, v_u_9.PlayerBlobRequestType.Write, function() --[[ Line: 536 ]]
                            --[[ Upvalues: (ref 1): v_u_35, (copy 2): v_u_252, (ref 3): p_u_245, (ref 4): p_u_55, (ref 5): p_u_29, (ref 6): v_u_7, (ref 7): p_u_244 ]]
                            v_u_35:dsapi_guild_add_star_currency(v_u_252, p_u_245, function(p253, p254) --[[ Line: 537 ]]
                                --[[ Upvalues: (ref 1): p_u_55, (ref 2): v_u_252, (ref 3): p_u_29, (ref 4): v_u_7, (ref 5): p_u_244, (ref 6): p_u_245 ]]
                                if p253 then
                                    p_u_55:validate_web_table_to_guild_data_cache(v_u_252, p254)
                                    p_u_29._evt:fire_event_to_client(v_u_7.EVT_Guild_DonateStars_ServerResponse, p_u_244, true, "", p254)
                                    p_u_29._guild_manager:player_write_guild_message_text(p_u_244, string.format("%s donated %d Stars to the team.", p_u_244.Name, p_u_245))
                                end;
                            end)
                        end, false, function(p255) --[[ Line: 549 ]]
                            --[[ Upvalues: (ref 1): v_u_6, (ref 2): p_u_245, (copy 3): v_u_252 ]]
                            p255:set_guild_contribution(v_u_252, (v_u_6:contribution_source_to_points(v_u_6.ContributionSource.DonateStars, p_u_245)))
                        end)
                    end)
                end)
            end)
            local v_u_256 = v_u_27:new()
            p_u_29._evt:wait_on_event(v_u_7.EVT_Guild_EnterContributionWeek_Client, function(p_u_257, p_u_258) --[[ Line: 561 ]]
                --[[ Upvalues: (ref 1): v_u_8, (ref 2): v_u_17, (ref 3): v_u_4, (ref 4): p_u_29, (ref 5): v_u_7, (copy 6): p_u_55, (copy 7): v_u_256, (ref 8): v_u_10, (ref 9): v_u_6, (ref 10): v_u_35 ]]
                v_u_8:is_enum_member(p_u_258, v_u_17)
                v_u_4:get_player_id(p_u_257)
                local function f_response(p259, p260, p261) --[[ Name: response ]] --[[ Line: 564 ]]
                    --[[ Upvalues: (ref 1): p_u_29, (ref 2): v_u_7, (copy 3): p_u_257 ]]
                    p_u_29._evt:fire_event_to_client(v_u_7.EVT_Guild_EnterContributionWeek_ServerResponse, p_u_257, p259, p260, p261)
                end;
                local v262, v_u_263 = p_u_55:is_player_in_guild(p_u_257.UserId)
                if v262 ~= true then
                    return f_response(false, "Player not in team", nil);
                end;
                v_u_256:queue_key_request(v_u_263, function() --[[ Line: 571 ]]
                    --[[ Upvalues: (ref 1): p_u_55, (copy 2): v_u_263, (ref 3): v_u_10, (copy 4): p_u_257, (copy 5): f_response, (ref 6): v_u_6, (ref 7): v_u_35, (copy 8): p_u_258, (ref 9): p_u_29, (ref 10): v_u_7, (ref 11): v_u_17 ]]
                    p_u_55:get_guild_data(v_u_263, function(p264) --[[ Line: 572 ]]
                        --[[ Upvalues: (ref 1): v_u_10, (ref 2): p_u_257, (ref 3): f_response, (ref 4): v_u_6, (ref 5): v_u_35, (ref 6): v_u_263, (ref 7): p_u_258, (ref 8): p_u_55, (ref 9): p_u_29, (ref 10): v_u_7, (ref 11): v_u_17 ]]
                        if v_u_10:player_has_admin_access(p264, p_u_257.UserId) ~= true then
                            return f_response(false, "You do not have admin rank for this team", nil);
                        end;
                        if p264:get_current_week_contribution_entry():is_entered() then
                            return f_response(false, "Already entered for this week");
                        end;
                        local v_u_265 = v_u_6:get_guild_enter_weekly_contribution_leaderboard_cost_for_guild_data(p264)
                        if p264:get_star_currency() < v_u_265 then
                            return f_response(false, "Not enough team stars");
                        end;
                        v_u_35:dsapi_create_guild_week_contribution_entry(v_u_263, p_u_258, p264:get_star_currency(), function(p266, p267) --[[ Line: 577 ]]
                            --[[ Upvalues: (ref 1): p_u_55, (ref 2): v_u_263, (ref 3): f_response, (ref 4): v_u_35, (copy 5): v_u_265, (ref 6): p_u_29, (ref 7): v_u_7, (ref 8): p_u_257, (ref 9): v_u_17, (ref 10): p_u_258 ]]
                            if p266 ~= true then
                                p_u_55:clear_guildid_cache(v_u_263)
                                return f_response(false, "Backend error(1)");
                            end;
                            p_u_55:validate_web_table_to_guild_data_cache(v_u_263, p267)
                            v_u_35:dsapi_guild_add_star_currency(v_u_263, -v_u_265, function(p268, p269) --[[ Line: 580 ]]
                                --[[ Upvalues: (ref 1): p_u_55, (ref 2): v_u_263, (ref 3): f_response, (ref 4): p_u_29, (ref 5): v_u_7, (ref 6): p_u_257, (ref 7): v_u_17, (ref 8): p_u_258 ]]
                                if p268 ~= true then
                                    p_u_55:clear_guildid_cache(v_u_263)
                                    return f_response(false, "Backend error(2)");
                                end;
                                p_u_55:validate_web_table_to_guild_data_cache(v_u_263, p269)
                                p_u_29._evt:fire_event_to_client(v_u_7.EVT_Guild_EnterContributionWeek_ServerResponse, p_u_257, true, "", p269)
                                p_u_29._guild_manager:player_write_guild_message_text(p_u_257, string.format("%s entered team to weekly leaderboard for element \'%s\'.", p_u_257.Name, v_u_17:color_to_name(p_u_258)))
                            end)
                        end)
                    end)
                end)
            end)
            p_u_29._evt:wait_on_event(v_u_7.EVT_Guild_ClaimContributionBuff_Client, function(p_u_270) --[[ Line: 595 ]]
                --[[ Upvalues: (ref 1): v_u_4, (ref 2): p_u_29, (ref 3): v_u_7, (copy 4): p_u_55, (ref 5): v_u_10, (ref 6): v_u_6, (ref 7): v_u_3, (ref 8): v_u_24, (ref 9): v_u_5, (ref 10): v_u_23 ]]
                local v_u_271 = v_u_4:get_player_id(p_u_270)
                local function f_response(p272, p273, p274) --[[ Name: response ]] --[[ Line: 597 ]]
                    --[[ Upvalues: (ref 1): p_u_29, (ref 2): v_u_7, (copy 3): p_u_270 ]]
                    p_u_29._evt:fire_event_to_client(v_u_7.EVT_Guild_ClaimContributionBuff_ServerResponse, p_u_270, p272, p273, p274 == nil and {} or p274)
                end;
                local v275, v276 = p_u_55:is_player_in_guild(v_u_271)
                if v275 ~= true then
                    return f_response(false, "Player not in team");
                end;
                p_u_55:get_guild_data(v276, function(p_u_277) --[[ Line: 604 ]]
                    --[[ Upvalues: (ref 1): v_u_10, (copy 2): v_u_271, (copy 3): f_response, (ref 4): p_u_29, (ref 5): v_u_6, (ref 6): v_u_3, (ref 7): v_u_24, (ref 8): v_u_5, (ref 9): v_u_23, (copy 10): p_u_270, (ref 11): v_u_7 ]]
                    local v_u_278 = p_u_277:get_last_week_contribution_entry()
                    if v_u_10:get_player_info(p_u_277, v_u_271) == nil then
                        return f_response(false, "Member not found");
                    end;
                    p_u_29._player_blob_manager:get_verified_cached_blob(v_u_271, function(p_u_279) --[[ Line: 609 ]]
                        --[[ Upvalues: (ref 1): v_u_10, (copy 2): p_u_277, (ref 3): v_u_271, (ref 4): f_response, (ref 5): p_u_29, (copy 6): v_u_278, (ref 7): v_u_6, (ref 8): v_u_3, (ref 9): v_u_24, (ref 10): v_u_5, (ref 11): v_u_23, (ref 12): p_u_270, (ref 13): v_u_7 ]]
                        local v280, v_u_281, v_u_282 = v_u_10:member_playerblob_can_claim_weekly_buff(p_u_277, p_u_279, v_u_271)
                        if v280 ~= true then
                            return f_response(false, v_u_281);
                        end;
                        if v_u_282 ~= p_u_29._api:get_week_id() then
                            return f_response(false, "unexpected apply_week id");
                        end;
                        p_u_279.TeamBuffWeekID = v_u_282
                        p_u_279.TeamBuffColor = v_u_278:get_selected_color()
                        p_u_279.TeamBuffLevel = v_u_6:contribution_entry_to_buff_level(v_u_278)
                        p_u_29._datastore_api:datastore_api_get_team_leaderboard_can_claim(v_u_271, v_u_282, function(p283) --[[ Line: 618 ]]
                            --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_6, (ref 3): v_u_278, (ref 4): p_u_29, (ref 5): v_u_24, (ref 6): v_u_271, (copy 7): v_u_282, (copy 8): v_u_281, (ref 9): v_u_5, (ref 10): v_u_23, (copy 11): p_u_279, (ref 12): p_u_270, (ref 13): v_u_7 ]]
                            local v284 = v_u_3:new()
                            if p283 == true then
                                v284 = v_u_6:contribution_entry_to_reward_list(v_u_278)
                                p_u_29._api:api_report_evt(v_u_24.ReportEvt_TeamLeaderboardClaimSuccess, v_u_271, v_u_282, (tostring(v_u_281)))
                            else
                                p_u_29._api:api_report_evt(v_u_24.ReportEvt_UnexpectedClaimTeamLeaderboard, v_u_271, v_u_282, (tostring(v_u_281)))
                                v_u_5:warnf("ReportEvt_UnexpectedClaimTeamLeaderboard(%s,%s,%s)", tostring(v_u_271), tostring(v_u_282), (tostring(v_u_281)))
                            end;
                            v_u_23:server_sync_reward_params(p_u_29, p_u_270, v_u_23:claim_reward_info_list_to_playerblob(p_u_29, p_u_279, v284), function(_, _, p_u_285) --[[ Line: 643 ]]
                                --[[ Upvalues: (ref 1): p_u_29, (ref 2): v_u_271, (ref 3): v_u_282, (ref 4): v_u_23, (ref 5): v_u_7, (ref 6): p_u_270 ]]
                                p_u_29._datastore_api:datastore_api_get_team_leaderboard_set_claimed(v_u_271, v_u_282, function() --[[ Line: 644 ]]
                                    --[[ Upvalues: (ref 1): v_u_23, (copy 2): p_u_285, (ref 3): p_u_29, (ref 4): v_u_7, (ref 5): p_u_270 ]]
                                    local v286 = v_u_23.RewardInfo:list_to_table(p_u_285)
                                    p_u_29._evt:fire_event_to_client(v_u_7.EVT_Guild_ClaimContributionBuff_ServerResponse, p_u_270, true, "", v286 == nil and {} or v286)
                                end)
                            end)
                        end)
                    end)
                end)
            end)
            p_u_29._evt:wait_on_event(v_u_7.EVT_Guild_GetLeaderboardInfo_Client, function(p_u_287) --[[ Line: 654 ]]
                --[[ Upvalues: (ref 1): v_u_4, (copy 2): p_u_55, (ref 3): p_u_29, (ref 4): v_u_7 ]]
                local _, v_u_288 = p_u_55:is_player_in_guild((v_u_4:get_player_id(p_u_287)))
                p_u_55:get_global_contribution_leaderboard_data(function(p_u_289) --[[ Line: 657 ]]
                    --[[ Upvalues: (ref 1): p_u_55, (copy 2): v_u_288, (ref 3): p_u_29, (ref 4): v_u_7, (copy 5): p_u_287 ]]
                    p_u_55:get_guildid_contribution_leaderboard_status(v_u_288, function(p290) --[[ Line: 658 ]]
                        --[[ Upvalues: (ref 1): p_u_29, (ref 2): v_u_7, (ref 3): p_u_287, (copy 4): p_u_289 ]]
                        p_u_29._evt:fire_event_to_client(v_u_7.EVT_Guild_GetLeaderboardInfo_ServerResponse, p_u_287, p_u_289, p290)
                    end)
                end)
            end)
            local v_u_291 = v_u_27:new()
            p_u_29._evt:wait_on_event(v_u_7.EVT_Guild_AddGuildBonus_Client, function(p_u_292, p_u_293) --[[ Line: 666 ]]
                --[[ Upvalues: (ref 1): v_u_8, (ref 2): v_u_20, (ref 3): v_u_4, (ref 4): p_u_29, (ref 5): v_u_7, (copy 6): p_u_55, (copy 7): v_u_291, (ref 8): v_u_10, (ref 9): v_u_35 ]]
                v_u_8:is_enum_member(p_u_293, v_u_20.BonusType)
                local v_u_294 = v_u_4:get_player_id(p_u_292)
                local function f_response(p295, p296, p297) --[[ Name: response ]] --[[ Line: 670 ]]
                    --[[ Upvalues: (ref 1): p_u_29, (ref 2): v_u_7, (copy 3): p_u_292 ]]
                    p_u_29._evt:fire_event_to_client(v_u_7.EVT_Guild_AddGuildBonus_ServerResponse, p_u_292, p295, p296, p297)
                end;
                local v298, v_u_299 = p_u_55:is_player_in_guild(v_u_294)
                if v298 ~= true then
                    return f_response(false, "Player not in team");
                end;
                v_u_291:queue_key_request(v_u_299, function() --[[ Line: 677 ]]
                    --[[ Upvalues: (ref 1): p_u_55, (copy 2): v_u_299, (ref 3): v_u_10, (copy 4): v_u_294, (copy 5): f_response, (ref 6): v_u_20, (copy 7): p_u_293, (ref 8): p_u_29, (ref 9): v_u_7, (copy 10): p_u_292, (ref 11): v_u_35 ]]
                    p_u_55:get_guild_data(v_u_299, function(p300) --[[ Line: 678 ]]
                        --[[ Upvalues: (ref 1): v_u_10, (ref 2): v_u_294, (ref 3): f_response, (ref 4): v_u_20, (ref 5): p_u_293, (ref 6): p_u_29, (ref 7): v_u_7, (ref 8): p_u_292, (ref 9): v_u_35, (ref 10): v_u_299, (ref 11): p_u_55 ]]
                        if v_u_10:player_has_admin_access(p300, v_u_294) ~= true then
                            return f_response(false, "You do not have admin rank for this team");
                        end;
                        if v_u_20:guild_data_can_activate_bonus_id_for_weekid(p300, p_u_293, p_u_29._api:get_week_id()) ~= true then
                            p_u_29._evt:fire_event_to_client(v_u_7.EVT_Guild_AddGuildBonus_ServerResponse, p_u_292, false, "Guild bonus has already been activated for this week", nil)
                        end;
                        local v301 = v_u_20:guild_data_get_bonus_id_price(p300, p_u_293)
                        if p300:get_star_currency() < v301 then
                            return f_response(false, "Not enough team stars");
                        end;
                        local v_u_302 = v_u_20:guild_data_get_updated_flag_with_bonus_id_claimed_for_weekid(p300, p_u_293, p_u_29._api:get_week_id())
                        v_u_35:dsapi_guild_add_star_currency(v_u_299, -v301, function(p303, p304) --[[ Line: 690 ]]
                            --[[ Upvalues: (ref 1): p_u_55, (ref 2): v_u_299, (ref 3): f_response, (ref 4): v_u_35, (copy 5): v_u_302, (ref 6): p_u_29, (ref 7): v_u_7, (ref 8): p_u_292, (ref 9): v_u_20, (ref 10): p_u_293 ]]
                            if p303 ~= true then
                                p_u_55:clear_guildid_cache(v_u_299)
                                return f_response(false, "Backend error(1)");
                            end;
                            p_u_55:validate_web_table_to_guild_data_cache(v_u_299, p304)
                            v_u_35:dsapi_add_guild_bonus_entry(v_u_299, v_u_302, function(p305, p306) --[[ Line: 693 ]]
                                --[[ Upvalues: (ref 1): p_u_55, (ref 2): v_u_299, (ref 3): f_response, (ref 4): p_u_29, (ref 5): v_u_7, (ref 6): p_u_292, (ref 7): v_u_20, (ref 8): p_u_293 ]]
                                if p305 ~= true then
                                    p_u_55:clear_guildid_cache(v_u_299)
                                    return f_response(false, "Backend error(2)");
                                end;
                                p_u_55:validate_web_table_to_guild_data_cache(v_u_299, p306)
                                p_u_29._evt:fire_event_to_client(v_u_7.EVT_Guild_AddGuildBonus_ServerResponse, p_u_292, true, "", p306)
                                p_u_29._guild_manager:player_write_guild_message_text(p_u_292, string.format("%s purchased the Team Bonus \'%s\'.", p_u_292.Name, v_u_20:get_bonus_info_for_id(p_u_293):get_name()))
                            end)
                        end)
                    end)
                end)
            end)
            p_u_29._evt:wait_on_event(v_u_7.EVT_Guild_ClaimBonus_Client, function(p_u_307) --[[ Line: 710 ]]
                --[[ Upvalues: (ref 1): v_u_4, (ref 2): p_u_29, (ref 3): v_u_7, (copy 4): p_u_55, (ref 5): v_u_10, (ref 6): v_u_20, (ref 7): v_u_9 ]]
                local v_u_308 = v_u_4:get_player_id(p_u_307)
                local function f_response(p309, p310) --[[ Name: response ]] --[[ Line: 712 ]]
                    --[[ Upvalues: (ref 1): p_u_29, (ref 2): v_u_7, (copy 3): p_u_307 ]]
                    p_u_29._evt:fire_event_to_client(v_u_7.EVT_Guild_ClaimBonus_ServerResponse, p_u_307, p309, p310)
                end;
                local v311, v312 = p_u_55:is_player_in_guild(v_u_308)
                if v311 ~= true then
                    return f_response(false, "Player not in team");
                end;
                p_u_55:get_guild_data(v312, function(p_u_313) --[[ Line: 718 ]]
                    --[[ Upvalues: (ref 1): v_u_10, (copy 2): v_u_308, (copy 3): f_response, (ref 4): p_u_29, (ref 5): v_u_20, (ref 6): v_u_9, (ref 7): v_u_7, (copy 8): p_u_307 ]]
                    if v_u_10:get_player_info(p_u_313, v_u_308) == nil then
                        return f_response(false, "Member not found");
                    end;
                    p_u_29._player_blob_manager:get_verified_cached_blob(v_u_308, function(p314) --[[ Line: 722 ]]
                        --[[ Upvalues: (ref 1): v_u_20, (copy 2): p_u_313, (ref 3): p_u_29, (ref 4): f_response, (ref 5): v_u_308, (ref 6): v_u_9, (ref 7): v_u_7, (ref 8): p_u_307 ]]
                        local v315, _, v316 = v_u_20:playerblob_guild_data_can_claim_any_bonus_for_weekid(p314, p_u_313, p_u_29._api:get_week_id())
                        if v315 ~= true then
                            return f_response(false, v316);
                        end;
                        p314.TeamBonusWeekID = p_u_313:get_bonus_weekid()
                        p314.TeamBonusClaimed = p_u_313:get_bonus_flag()
                        p_u_29._player_blob_manager:enqueue_blob_sync_request(v_u_308, v_u_9.PlayerBlobRequestType.Write, function() --[[ Line: 732 ]]
                            --[[ Upvalues: (ref 1): p_u_29, (ref 2): v_u_7, (ref 3): p_u_307 ]]
                            p_u_29._evt:fire_event_to_client(v_u_7.EVT_Guild_ClaimBonus_ServerResponse, p_u_307, true, "")
                        end)
                    end)
                end)
            end)
            p_u_29._evt:wait_on_event(v_u_7.EVT_Guild_GetGuildActivityLogClient, function(p_u_317) --[[ Line: 740 ]]
                --[[ Upvalues: (ref 1): p_u_29, (ref 2): v_u_7, (ref 3): v_u_25, (copy 4): p_u_55, (ref 5): v_u_3 ]]
                local function f_response(p318) --[[ Name: response ]] --[[ Line: 741 ]]
                    --[[ Upvalues: (ref 1): p_u_29, (ref 2): v_u_7, (copy 3): p_u_317, (ref 4): v_u_25 ]]
                    p_u_29._evt:fire_event_to_client(v_u_7.EVT_Guild_GetGuildActivityLogServerResponse, p_u_317, v_u_25:list_to_table(p318))
                end;
                local v319, v320 = p_u_55:is_player_in_guild(p_u_317.UserId)
                if v319 ~= true then
                    return f_response(v_u_3:new());
                end;
                p_u_29._datastore_api:get_guildid_activity_log_messages(v320, function(p321) --[[ Line: 746 ]]
                    --[[ Upvalues: (ref 1): p_u_29, (ref 2): v_u_7, (copy 3): p_u_317, (ref 4): v_u_25 ]]
                    p_u_29._evt:fire_event_to_client(v_u_7.EVT_Guild_GetGuildActivityLogServerResponse, p_u_317, v_u_25:list_to_table(p321))
                end)
            end)
            p_u_29._evt:wait_on_event(v_u_7.EVT_Guild_GetGuildMessageBoardClient, function(p_u_322) --[[ Line: 751 ]]
                --[[ Upvalues: (ref 1): p_u_29, (ref 2): v_u_7, (ref 3): v_u_25, (copy 4): p_u_55, (ref 5): v_u_3 ]]
                local function f_response(p323) --[[ Name: response ]] --[[ Line: 752 ]]
                    --[[ Upvalues: (ref 1): p_u_29, (ref 2): v_u_7, (copy 3): p_u_322, (ref 4): v_u_25 ]]
                    p_u_29._evt:fire_event_to_client(v_u_7.EVT_Guild_GetGuildMessageBoardServerResponse, p_u_322, v_u_25:list_to_table(p323))
                end;
                local v324, v325 = p_u_55:is_player_in_guild(p_u_322.UserId)
                if v324 ~= true then
                    return f_response(v_u_3:new());
                end;
                p_u_29._datastore_api:get_guildid_message_board_messages(v325, function(p326) --[[ Line: 757 ]]
                    --[[ Upvalues: (ref 1): p_u_29, (ref 2): v_u_7, (copy 3): p_u_322, (ref 4): v_u_25 ]]
                    p_u_29._evt:fire_event_to_client(v_u_7.EVT_Guild_GetGuildMessageBoardServerResponse, p_u_322, v_u_25:list_to_table(p326))
                end)
            end)
            local v_u_327 = v_u_27:new():set_cooldown(5)
            p_u_29._evt:wait_on_event(v_u_7.EVT_Guild_PostGuildMessageClient, function(p_u_328, p_u_329) --[[ Line: 764 ]]
                --[[ Upvalues: (ref 1): v_u_8, (copy 2): v_u_327, (ref 3): v_u_3, (ref 4): p_u_29, (ref 5): v_u_7, (ref 6): v_u_25, (copy 7): p_u_55, (ref 8): v_u_40, (ref 9): v_u_4, (ref 10): v_u_26, (ref 11): v_u_9 ]]
                v_u_8:is_string(p_u_329)
                v_u_327:queue_key_request(p_u_328.UserId, function() --[[ Line: 766 ]]
                    --[[ Upvalues: (ref 1): v_u_3, (ref 2): p_u_29, (ref 3): v_u_7, (copy 4): p_u_328, (ref 5): v_u_25, (ref 6): p_u_55, (ref 7): v_u_40, (ref 8): v_u_4, (copy 9): p_u_329, (ref 10): v_u_26, (ref 11): v_u_9 ]]
                    local function f_response(p330, p331, p332, p333) --[[ Name: response ]] --[[ Line: 767 ]]
                        --[[ Upvalues: (ref 1): v_u_3, (ref 2): p_u_29, (ref 3): v_u_7, (ref 4): p_u_328, (ref 5): v_u_25 ]]
                        if p332 == nil then
                            p332 = v_u_3:new()
                        end;
                        if p333 == nil then
                            p333 = false
                        end;
                        p_u_29._evt:fire_event_to_client(v_u_7.EVT_Guild_PostGuildMessageServerResponse, p_u_328, p330, p331, v_u_25:list_to_table(p332), p333)
                    end;
                    local v334, v_u_335 = p_u_55:is_player_in_guild(p_u_328.UserId)
                    if v334 ~= true then
                        return f_response(false, "Player not in team");
                    end;
                    if v_u_40:is_on_cooldown(p_u_328.UserId) then
                        return f_response(false, "Posting Team Message on cooldown");
                    end;
                    v_u_4:spawn(function() --[[ Line: 777 ]]
                        --[[ Upvalues: (ref 1): v_u_4, (ref 2): p_u_329, (ref 3): p_u_328, (copy 4): f_response, (ref 5): p_u_29, (ref 6): v_u_40, (copy 7): v_u_335, (ref 8): v_u_25, (ref 9): v_u_26, (ref 10): v_u_9 ]]
                        local v_u_336 = v_u_4:filter_string(p_u_329, p_u_328, p_u_328)
                        if v_u_336 ~= p_u_329 then
                            return f_response(false, string.format("Message did not pass roblox moderation(%s)", v_u_336));
                        end;
                        p_u_29._post_fn:enqueue_function(function() --[[ Line: 782 ]]
                            --[[ Upvalues: (ref 1): v_u_40, (ref 2): p_u_328, (ref 3): p_u_29, (ref 4): v_u_335, (ref 5): v_u_25, (copy 6): v_u_336, (ref 7): v_u_26, (ref 8): f_response, (ref 9): v_u_9 ]]
                            v_u_40:add_cooldown_to_id(p_u_328.UserId, 2.5)
                            p_u_29._datastore_api:write_guildid_message_board_message(v_u_335, v_u_25:new():set_player_id_name(p_u_328.UserId, p_u_328.Name):set_message_time(p_u_29._api:get_global_time()):set_message_text(v_u_336), function(p_u_337) --[[ Line: 791 ]]
                                --[[ Upvalues: (ref 1): v_u_26, (ref 2): p_u_29, (ref 3): p_u_328, (ref 4): f_response, (ref 5): v_u_9 ]]
                                if v_u_26:can_claim_daily_mission_type_playerblob_dayid_monthid(v_u_26.DailyMissionType.PostTeamMessageBoard, p_u_29._player_blob_manager:get_cached_blob(p_u_328.UserId), p_u_29._api:get_day_id(), p_u_29._api:get_month_id()) ~= true then
                                    return f_response(true, "", p_u_337);
                                end;
                                p_u_29._player_blob_manager:get_verified_cached_blob(p_u_328.UserId, function(p338) --[[ Line: 793 ]]
                                    --[[ Upvalues: (ref 1): f_response, (copy 2): p_u_337, (ref 3): p_u_29, (ref 4): v_u_26, (ref 5): p_u_328, (ref 6): v_u_9 ]]
                                    if p338 == nil then
                                        return f_response(true, "", p_u_337);
                                    end;
                                    p_u_29._challengepass_manager:challengepassv2_daily_mission_playerblob_claim(v_u_26.DailyMissionType.PostTeamMessageBoard, p338)
                                    p_u_29._player_blob_manager:enqueue_blob_sync_request(p_u_328.UserId, v_u_9.PlayerBlobRequestType.Write, function(_) --[[ Line: 800 ]]
                                        --[[ Upvalues: (ref 1): f_response, (ref 2): p_u_337 ]]
                                        return f_response(true, "", p_u_337, true);
                                    end)
                                end)
                            end)
                        end)
                    end)
                end)
            end)
            local v_u_339 = v_u_1:new()
            p_u_29._evt:wait_on_event(v_u_7.EVT_Guild_GetLastWeekLeaderboardInfo_Client, function(p_u_340) --[[ Line: 817 ]]
                --[[ Upvalues: (ref 1): p_u_29, (ref 2): v_u_7, (copy 3): v_u_339, (ref 4): v_u_35, (ref 5): v_u_10, (ref 6): v_u_5 ]]
                local function f_response(p341) --[[ Name: response ]] --[[ Line: 818 ]]
                    --[[ Upvalues: (ref 1): p_u_29, (ref 2): v_u_7, (copy 3): p_u_340 ]]
                    p_u_29._evt:fire_event_to_client(v_u_7.EVT_Guild_GetLastWeekLeaderboardInfo_ServerResponse, p_u_340, p341)
                end;
                local v_u_342 = p_u_29._api:get_week_id() - 1
                if v_u_339:contains(v_u_342) then
                    return f_response(v_u_339:get(v_u_342));
                end;
                v_u_35:dsapi_guild_get_previous_week_global_contribution_leaderboard(v_u_342, 25, function(p343, p_u_344) --[[ Line: 827 ]]
                    --[[ Upvalues: (ref 1): v_u_10, (ref 2): v_u_5, (ref 3): v_u_339, (copy 4): v_u_342, (ref 5): p_u_29, (ref 6): v_u_7, (copy 7): p_u_340 ]]
                    local v_u_345 = {}
                    if p343 then
                        local v348, v349 = pcall(function() --[[ Line: 830 ]]
                            --[[ Upvalues: (ref 1): v_u_10, (copy 2): p_u_344, (copy 3): v_u_345 ]]
                            for v346, v347 in v_u_10:table_list_to_list(p_u_344):key_itr() do
                                v_u_10:clear_private_data(v347)
                                v_u_345[v346] = v347:to_table()
                            end;
                        end)
                        if v348 ~= true then
                            v_u_5:warnf("_server._api:api_guild_get_global_contribution_leaderboard failed(%s)", v349)
                        end;
                    end;
                    v_u_339:add(v_u_342, v_u_345)
                    p_u_29._evt:fire_event_to_client(v_u_7.EVT_Guild_GetLastWeekLeaderboardInfo_ServerResponse, p_u_340, v_u_345)
                end)
            end)
        end;
        local v_u_350 = {}
        local v_u_351 = -1
        local v_u_359 = v_u_18:new(function(_, p_u_352) --[[ Line: 851 ]]
            --[[ Upvalues: (ref 1): v_u_351, (copy 2): v_u_35, (ref 3): v_u_350, (ref 4): v_u_10, (ref 5): v_u_5 ]]
            if os.time() - v_u_351 > 150 then
                v_u_35:dsapi_guild_get_global_contribution_leaderboard(function(p353, p_u_354) --[[ Line: 853 ]]
                    --[[ Upvalues: (ref 1): v_u_350, (ref 2): v_u_10, (ref 3): v_u_5, (ref 4): v_u_351, (copy 5): p_u_352 ]]
                    v_u_350 = {}
                    if p353 then
                        local v357, v358 = pcall(function() --[[ Line: 856 ]]
                            --[[ Upvalues: (ref 1): v_u_10, (copy 2): p_u_354, (ref 3): v_u_350 ]]
                            for v355, v356 in v_u_10:table_list_to_list(p_u_354):key_itr() do
                                v_u_10:clear_private_data(v356)
                                v_u_350[v355] = v356:to_table()
                            end;
                        end)
                        if v357 ~= true then
                            v_u_5:warnf("_server._api:api_guild_get_global_contribution_leaderboard failed(%s)", v358)
                        end;
                    end;
                    v_u_351 = os.time()
                    p_u_352(v_u_350)
                end)
            else
                p_u_352(v_u_350)
            end;
        end)
        v30.get_global_contribution_leaderboard_data = function(_, p_u_360) --[[ Name: get_global_contribution_leaderboard_data ]] --[[ Line: 874 ]]
            --[[ Upvalues: (copy 1): v_u_359 ]]
            v_u_359:queue_sequential(nil, function(p361) --[[ Line: 875 ]]
                --[[ Upvalues: (copy 1): p_u_360 ]]
                p_u_360(p361)
            end)
        end;
        local v_u_362 = v_u_1:new()
        v30.clear_cache_guildid_to_cached_contribution_leaderboard_status = function(_, p363) --[[ Name: clear_cache_guildid_to_cached_contribution_leaderboard_status ]] --[[ Line: 881 ]]
            --[[ Upvalues: (copy 1): v_u_362 ]]
            v_u_362:remove(p363)
        end;
        v30.get_guildid_contribution_leaderboard_status = function(_, p_u_364, p_u_365) --[[ Name: get_guildid_contribution_leaderboard_status ]] --[[ Line: 882 ]]
            --[[ Upvalues: (ref 1): v_u_6, (copy 2): v_u_362, (copy 3): v_u_35, (ref 4): v_u_10, (ref 5): v_u_5, (copy 6): v_u_36, (ref 7): v_u_15 ]]
            if p_u_364 == v_u_6:not_in_guild_id() then
                return p_u_365({});
            end;
            if v_u_362:contains(p_u_364) then
                return p_u_365(v_u_362:get(p_u_364));
            end;
            v_u_35:dsapi_get_contribution_leaderboard_status(p_u_364, function(p366, p_u_367) --[[ Line: 887 ]]
                --[[ Upvalues: (ref 1): v_u_10, (ref 2): v_u_5, (ref 3): v_u_362, (copy 4): p_u_364, (ref 5): v_u_36, (ref 6): v_u_15, (copy 7): p_u_365 ]]
                local v_u_368 = {}
                if p366 then
                    local v369, v370 = pcall(function() --[[ Line: 890 ]]
                        --[[ Upvalues: (copy 1): p_u_367, (copy 2): v_u_368, (ref 3): v_u_10 ]]
                        if p_u_367.YourTeam ~= nil then
                            v_u_368.YourTeam = v_u_10:from_table(p_u_367.YourTeam):to_table()
                        end;
                        if p_u_367.NextTeam ~= nil then
                            v_u_368.NextTeam = v_u_10:from_table(p_u_367.NextTeam):to_table()
                        end;
                        if p_u_367.PrevTeam ~= nil then
                            v_u_368.PrevTeam = v_u_10:from_table(p_u_367.PrevTeam):to_table()
                        end;
                    end)
                    if v369 ~= true then
                        v_u_5:warnf("_server._api:api_get_contribution_leaderboard_status failed(%s)", v370)
                    end;
                end;
                v_u_362:add(p_u_364, v_u_368)
                v_u_36:add(p_u_364, v_u_15.GUILD_DATA_CACHE_TIME_SEC)
                p_u_365(v_u_368)
            end)
        end;
        v30.validate_web_table_to_guild_data_cache = function(p371, p372, p373) --[[ Name: validate_web_table_to_guild_data_cache ]] --[[ Line: 912 ]]
            --[[ Upvalues: (ref 1): v_u_10, (ref 2): v_u_8, (ref 3): v_u_1, (copy 4): v_u_31, (ref 5): v_u_5, (copy 6): p_u_29, (ref 7): v_u_13, (ref 8): v_u_6, (copy 9): v_u_32, (copy 10): v_u_33, (copy 11): v_u_36, (ref 12): v_u_15 ]]
            local v374 = v_u_10:from_table(p373)
            v_u_8:is_true(v374:get_guildid() == p372, "validate_web_table_to_guild_data_cache guildid does not match")
            local v375 = v_u_10:playerid_set(v374)
            local v376 = v_u_1:new()
            for v377, v378 in v_u_31:key_itr() do
                if v378 == p372 then
                    v376:add(v377, true)
                end;
            end;
            for v379, _ in v376:key_itr() do
                if v375:contains(v379) ~= true then
                    v_u_31:remove(v379)
                    v_u_5:warnf("ServerGuildManager:validate_web_table_to_guild_data_cache _rbxid_to_guildid contained playerid(%d) but was not present in web table", v379)
                end;
            end;
            for v380, _ in v375:key_itr() do
                if v_u_31:contains(v380) ~= true and p_u_29._player_blob_manager:get_cached_blob(v380) ~= nil then
                    v_u_31:add(v380, p372)
                    v_u_5:warnf("ServerGuildManager:validate_web_table_to_guild_data_cache _rbxid_to_guildid did not contain playerid(%d) but was present in table", v380)
                end;
            end;
            if v_u_13.DebugGuildShowExtraMembers then
                for v381 = 1, 15 do
                    if v374:get_member_infos():count() < v_u_6:get_max_guild_players() then
                        v374:get_member_infos():push_back(v_u_10.MemberInfo:new(v381, string.format("DebugMember%d", v381), v381 % 2 + 1))
                    end;
                end;
            end;
            v_u_32:add(p372, v374)
            v_u_33:add(p372, v374)
            p371:clear_cache_guildid_to_cached_contribution_leaderboard_status(p372)
            v_u_36:add(p372, v_u_15.GUILD_DATA_CACHE_TIME_SEC)
            return v374;
        end;
        local v_u_382 = v_u_2:new()
        v30.get_guild_data = function(p_u_383, p_u_384, p385) --[[ Name: get_guild_data ]] --[[ Line: 958 ]]
            --[[ Upvalues: (copy 1): v_u_32, (copy 2): v_u_382, (ref 3): v_u_5, (copy 4): v_u_35, (ref 5): v_u_10, (ref 6): v_u_6 ]]
            if v_u_32:contains(p_u_384) then
                p385(v_u_32:get(p_u_384))
            else
                local v386 = v_u_382:count_of(p_u_384) == 0
                v_u_382:push_back_to(p_u_384, p385)
                if v386 then
                    v_u_5:puts("get_guild_data(%d) do_request", p_u_384)
                    v_u_35:dsapi_guild_get_data(p_u_384, function(p387, p388) --[[ Line: 966 ]]
                        --[[ Upvalues: (copy 1): p_u_383, (copy 2): p_u_384, (ref 3): v_u_5, (ref 4): v_u_10, (ref 5): v_u_6, (ref 6): v_u_382 ]]
                        local v389
                        if p387 then
                            v389 = p_u_383:validate_web_table_to_guild_data_cache(p_u_384, p388)
                        else
                            v_u_5:warnf("ServerGuildManager _api:api_guild_get_data(%d) failed, returning empty guild", p_u_384)
                            v389 = v_u_10:new(v_u_6:not_in_guild_id())
                        end;
                        local v390 = v_u_382:list_of(p_u_384)
                        local v391 = v390:count()
                        for _, v392 in v390:key_itr() do
                            v392(v389)
                        end;
                        v390:clear()
                        if v391 > 1 then
                            v_u_5:puts("api_guild_get_data(%d) had(%d) callbacks", p_u_384, v391)
                        end;
                    end)
                end;
            end;
        end;
        v30.get_guild_data_cached = function(_, p393) --[[ Name: get_guild_data_cached ]] --[[ Line: 989 ]]
            --[[ Upvalues: (copy 1): v_u_33 ]]
            return v_u_33:get(p393);
        end;
        v30.clear_guildid_cache = function(p394, p395) --[[ Name: clear_guildid_cache ]] --[[ Line: 993 ]]
            --[[ Upvalues: (copy 1): v_u_32, (copy 2): v_u_36 ]]
            v_u_32:remove(p395)
            v_u_36:remove(p395)
            p394:clear_cache_guildid_to_cached_contribution_leaderboard_status(p395)
        end;
        v30.get_online_player_guild_data_list = function(p396, p_u_397) --[[ Name: get_online_player_guild_data_list ]] --[[ Line: 999 ]]
            --[[ Upvalues: (ref 1): v_u_1, (copy 2): v_u_31, (ref 3): v_u_3, (ref 4): v_u_21 ]]
            local v398 = v_u_1:new()
            for _, v399 in v_u_31:key_itr() do
                if v399 ~= -1 then
                    v398:add_set(v399)
                end;
            end;
            local v_u_400 = v_u_3:new()
            local function _() --[[ Name: on_completed ]] --[[ Line: 1007 ]]
                --[[ Upvalues: (copy 1): p_u_397, (copy 2): v_u_400 ]]
                p_u_397(v_u_400)
            end;
            if v398:count() == 0 then
                p_u_397(v_u_400)
            else
                local v_u_401 = v_u_21:new(v398:count(), function() --[[ Line: 1014 ]]
                    --[[ Upvalues: (copy 1): p_u_397, (copy 2): v_u_400 ]]
                    p_u_397(v_u_400)
                end)
                for v402, _ in v398:key_itr() do
                    p396:get_guild_data(v402, function(p403) --[[ Line: 1018 ]]
                        --[[ Upvalues: (copy 1): v_u_400, (copy 2): v_u_401 ]]
                        v_u_400:push_back(p403)
                        v_u_401:finish()
                    end)
                end;
            end;
        end;
        v30.handle_playerblob_extra = function(_, p404, p405) --[[ Name: handle_playerblob_extra ]] --[[ Line: 1026 ]]
            --[[ Upvalues: (copy 1): v_u_31 ]]
            if p405.GuildID ~= nil then
                v_u_31:add(p404, p405.GuildID)
            end;
        end;
        v30.player_disconnecting = function(_, p406) --[[ Name: player_disconnecting ]] --[[ Line: 1032 ]]
            --[[ Upvalues: (copy 1): v_u_34, (copy 2): v_u_31 ]]
            v_u_34:player_disconnecting(p406)
            v_u_31:remove(p406)
        end;
        v30.update = function(p_u_407, p408) --[[ Name: update ]] --[[ Line: 1037 ]]
            --[[ Upvalues: (copy 1): v_u_40, (copy 2): v_u_41, (ref 3): v_u_16, (ref 4): v_u_1, (copy 5): v_u_36, (copy 6): v_u_32, (copy 7): v_u_37, (copy 8): v_u_34, (copy 9): v_u_35 ]]
            v_u_40:update(p408)
            v_u_41:update(p408)
            local v_u_409 = v_u_16:TimescaleToDeltaTime(p408)
            v_u_1:remove_if(v_u_36, function(p410, p411) --[[ Line: 1045 ]]
                --[[ Upvalues: (copy 1): v_u_409, (ref 2): v_u_32, (copy 3): p_u_407, (ref 4): v_u_36 ]]
                local v412 = p410 - v_u_409
                if v412 > 0 then
                    v_u_36:add(p411, v412)
                    return false;
                end;
                v_u_32:remove(p411)
                p_u_407:clear_cache_guildid_to_cached_contribution_leaderboard_status(p411)
                return true;
            end)
            v_u_1:remove_if(v_u_37, function(p413, p414) --[[ Line: 1059 ]]
                --[[ Upvalues: (copy 1): v_u_409, (ref 2): v_u_37 ]]
                local v415 = p413 - v_u_409
                if v415 <= 0 then
                    return true;
                end;
                v_u_37:add(p414, v415)
                return false;
            end)
            v_u_34:update(p408)
            v_u_35:update(p408)
        end;
        v30.day_update = function(p416) --[[ Name: day_update ]] --[[ Line: 1074 ]]
            --[[ Upvalues: (copy 1): v_u_32 ]]
            for _, v417 in v_u_32:key_list():key_itr() do
                p416:clear_guildid_cache(v417)
            end;
        end;
        v30.get_debug_str = function(_) --[[ Name: get_debug_str ]] --[[ Line: 1081 ]]
            --[[ Upvalues: (copy 1): v_u_31, (copy 2): v_u_32, (copy 3): v_u_37, (copy 4): v_u_34 ]]
            return string.format("_rbxid_to_guildid(%d) _guildid_to_data(%d) _invite_key_to_time(%d) recruitment(%s)", v_u_31:count(), v_u_32:count(), v_u_37:count(), v_u_34:get_debug_str());
        end;
        v30.player_write_guild_message_text = function(p418, p419, p420, p421) --[[ Name: player_write_guild_message_text ]] --[[ Line: 1085 ]]
            --[[ Upvalues: (copy 1): p_u_29, (ref 2): v_u_25 ]]
            local v422, v423 = p418:is_player_in_guild(p419.UserId)
            if typeof(p421) == "number" then
                v422 = true
            else
                p421 = v423
            end;
            if v422 == true then
                p_u_29._datastore_api:write_guildid_activity_log_message(p421, v_u_25:new():set_player_id_name(p419.UserId, p419.Name):set_message_time(p_u_29._api:get_global_time()):set_message_text(p420))
            end;
        end;
        return v30;
    end
};
