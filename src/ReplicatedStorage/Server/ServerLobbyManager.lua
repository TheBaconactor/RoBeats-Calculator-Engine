-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:14 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.ServerGameInstancePlayer)
require(game.ReplicatedStorage.Shared.FlashEvery)
require(game.ReplicatedStorage.Shared.NoteResult)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_6 = require(game.ReplicatedStorage.Avatar.PlayerBlobAvatar)
local v_u_7 = require(game.ReplicatedStorage.Avatar.SPAvatarUtil)
local v_u_8 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_9 = require(game.ReplicatedStorage.Server.ServerAPIManager)
local v_u_10 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_11 = require(game.ReplicatedStorage.Shared.Constants)
local v_u_12 = require(game.ReplicatedStorage.Avatar.PlayerBlobLoadout)
local v_u_13 = require(game.ReplicatedStorage.Shared.CooldownDelay)
local v_u_14 = require(game.ReplicatedStorage.Server.EnvironmentSetupServer)
require(game.ServerScriptService.SPDiveAPI)
local v_u_15 = require(game.ReplicatedStorage.Shared.GuildUtil)
local v_u_16 = require(game.ReplicatedStorage.Shared.WaitForFinish)
require(game.ReplicatedStorage.PlayerInfo.FeverIconDatabase)
local v_u_17 = require(game.ReplicatedStorage.SPChat.Shared.SPChatUtil)
local v_u_18 = require(game.ReplicatedStorage.Server.SpecialEvent.ServerEventLeaderboardManager)
local v_u_19 = require(game.ReplicatedStorage.Shared.HUDNotification)
local v_u_20 = require(game.ReplicatedStorage.Shared.FavoriteData)
local v_u_21 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_22 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_23 = require(game.ReplicatedStorage.Server.ServerLobbyFollowNPCManager)
local v_u_24 = require(game.ReplicatedStorage.Pets.PetUtils)
local v_u_25 = require(game.ReplicatedStorage.PlayerInfo.DanceDatabase)
local v_u_26 = require(game.ReplicatedStorage.PlayerInfo.GearSlotIncreaseUtil)
local v_u_27 = require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
local v_u_28 = require(game.ReplicatedStorage.Shared.PlayerSettings)
local v_u_29 = require(game.ReplicatedStorage.Shared.GuildMessage)
local v_u_30 = require(game.ReplicatedStorage.Shared.GenericMessageBoardUtil)
local v_u_31 = require(game.ReplicatedStorage.PlayerInfo.ChallengePassV2.ChallengePassV2Mission)
local v_u_32 = require(game.ReplicatedStorage.Shared.APICooldown)
local v_u_33 = require(game.ReplicatedStorage.EditorGame.Data.EditorExportData)
local v34 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_35 = nil
v34:require_server(function() --[[ Line: 43 ]]
    --[[ Upvalues: (ref 1): v_u_35 ]]
    v_u_35 = require(game.ReplicatedStorage.Server.SpecialEvent.ServerPetAssignmentManager)
end)
local v_u_36 = {}
local v_u_37 = v_u_2:new(require(game.ReplicatedStorage.CodeGen.PlayerSpawnCFrames))
local v_u_38 = v_u_5:rand_rangei(1, v_u_37:count())
v_u_36.get_random_cframe = function(_) --[[ Name: get_random_cframe ]] --[[ Line: 51 ]]
    --[[ Upvalues: (copy 1): v_u_37, (ref 2): v_u_38 ]]
    local v39 = v_u_37:get(v_u_38)
    v_u_38 = v_u_38 + 1
    if v_u_38 > v_u_37:count() then
        v_u_38 = 1
    end;
    return v39;
end;
return {
    ["new"] = function(_, p_u_40) --[[ Name: new ]] --[[ Line: 61 ]]
        --[[ Upvalues: (copy 1): v_u_17, (copy 2): v_u_15, (copy 3): v_u_3, (copy 4): v_u_13, (copy 5): v_u_23, (copy 6): v_u_4, (copy 7): v_u_5, (copy 8): v_u_1, (copy 9): v_u_36, (copy 10): v_u_7, (copy 11): v_u_6, (copy 12): v_u_8, (copy 13): v_u_14, (copy 14): v_u_19, (copy 15): v_u_18, (copy 16): v_u_16, (copy 17): v_u_24, (copy 18): v_u_12, (copy 19): v_u_11, (copy 20): v_u_25, (ref 21): v_u_35, (copy 22): v_u_32, (copy 23): v_u_22, (copy 24): v_u_21, (copy 25): v_u_20, (copy 26): v_u_26, (copy 27): v_u_27, (copy 28): v_u_9, (copy 29): v_u_28, (copy 30): v_u_30, (copy 31): v_u_33, (copy 32): v_u_29, (copy 33): v_u_2, (copy 34): v_u_31, (copy 35): v_u_10 ]]
        local v41 = {}
        local v_u_42 = {
            ["UserId"] = -1,
            ["MissionRank"] = 0,
            ["CurrentTitleID"] = 0
        }
        local function f_player_blob_get_info(p43, p_u_44) --[[ Name: player_blob_get_info ]] --[[ Line: 65 ]]
            --[[ Upvalues: (copy 1): v_u_42, (copy 2): p_u_40, (ref 3): v_u_17, (ref 4): v_u_15 ]]
            if p43 == nil then
                return p_u_44(v_u_42);
            else
                local v45, v_u_46 = p_u_40._guild_manager:is_player_in_guild(p43.UserId)
                local v47, v48 = v_u_17:playerblob_get_chat_icon(p43)
                local v_u_49 = {
                    ["UserId"] = p43.UserId,
                    ["MissionRank"] = p43.MissionRank,
                    ["CurrentTitleID"] = p43.CurrentTitleID,
                    ["IsInGuild"] = v45,
                    ["GuildId"] = v_u_15:not_in_guild_id(),
                    ["GuildName"] = "",
                    ["HasCustomIcon"] = v48,
                    ["CustomIcon"] = v47
                }
                if v45 == true then
                    p_u_40._guild_manager:get_guild_data(v_u_46, function(p50) --[[ Line: 85 ]]
                        --[[ Upvalues: (copy 1): v_u_49, (copy 2): v_u_46, (copy 3): p_u_44 ]]
                        v_u_49.GuildId = v_u_46
                        v_u_49.GuildName = p50:get_name()
                        p_u_44(v_u_49)
                    end)
                else
                    p_u_44(v_u_49)
                end;
            end;
        end;
        local v_u_51 = v_u_3:new()
        local v_u_52 = v_u_3:new()
        local v_u_53 = v_u_13:new()
        local v_u_54 = v_u_13:new()
        local v_u_55 = v_u_13:new()
        local v_u_56 = v_u_13:new()
        local v_u_57 = v_u_3:new()
        local v_u_58 = v_u_23:new(p_u_40)
        v41.get_follow_npc_manager = function(_) --[[ Name: get_follow_npc_manager ]] --[[ Line: 102 ]]
            --[[ Upvalues: (copy 1): v_u_58 ]]
            return v_u_58;
        end;
        v41.start = function(p_u_59) --[[ Name: start ]] --[[ Line: 105 ]]
            --[[ Upvalues: (copy 1): p_u_40, (ref 2): v_u_4, (ref 3): v_u_5, (ref 4): v_u_1, (ref 5): v_u_36, (ref 6): v_u_7, (ref 7): v_u_6, (ref 8): v_u_8, (ref 9): v_u_14, (ref 10): v_u_19, (ref 11): v_u_18, (copy 12): f_player_blob_get_info, (copy 13): v_u_58, (ref 14): v_u_16, (copy 15): v_u_56, (ref 16): v_u_24, (ref 17): v_u_12, (copy 18): v_u_51, (copy 19): v_u_52, (ref 20): v_u_11, (copy 21): v_u_53, (ref 22): v_u_25, (ref 23): v_u_35, (ref 24): v_u_32, (ref 25): v_u_22, (ref 26): v_u_21, (ref 27): v_u_20, (ref 28): v_u_26, (ref 29): v_u_27, (ref 30): v_u_9, (ref 31): v_u_28, (ref 32): v_u_30, (ref 33): v_u_33, (ref 34): v_u_29, (ref 35): v_u_2, (copy 36): v_u_55, (ref 37): v_u_31 ]]
            p_u_40._evt:wait_on_event(v_u_4.EVT_Lobby_ClientNotifyEnter, function(p_u_60, p_u_61, p_u_62) --[[ Line: 106 ]]
                --[[ Upvalues: (ref 1): v_u_5, (ref 2): p_u_40, (ref 3): v_u_1, (ref 4): v_u_36, (copy 5): p_u_59, (ref 6): v_u_7, (ref 7): v_u_6, (ref 8): v_u_8, (ref 9): v_u_4, (ref 10): v_u_14, (ref 11): v_u_19, (ref 12): v_u_18, (ref 13): f_player_blob_get_info, (ref 14): v_u_58 ]]
                local v_u_63 = v_u_5:get_player_id(p_u_60)
                p_u_40._player_model_cache:load_character_for_player(p_u_60, function() --[[ Line: 109 ]]
                    --[[ Upvalues: (copy 1): p_u_60, (ref 2): v_u_1, (ref 3): v_u_5, (copy 4): p_u_61, (ref 5): p_u_62, (ref 6): v_u_36, (ref 7): p_u_59, (ref 8): p_u_40, (copy 9): v_u_63, (ref 10): v_u_7, (ref 11): v_u_6, (ref 12): v_u_8, (ref 13): v_u_4, (ref 14): v_u_14, (ref 15): v_u_19, (ref 16): v_u_18, (ref 17): f_player_blob_get_info, (ref 18): v_u_58 ]]
                    if p_u_60.Character == nil then
                        v_u_1:errf("EVT_Lobby_ClientNotifyEnter character is nil")
                    end;
                    local v_u_64 = p_u_60.Character:FindFirstChild("Humanoid")
                    if v_u_64 == nil then
                        v_u_1:errf("EVT_Lobby_ClientNotifyEnter humanoid is nil")
                    end;
                    local l_RootPart_0 = v_u_64.RootPart
                    if l_RootPart_0 == nil then
                        v_u_1:errf("EVT_Lobby_ClientNotifyEnter root_part is nil")
                    end;
                    l_RootPart_0.Anchored = true
                    v_u_5:ptry(function() --[[ Line: 117 ]]
                        --[[ Upvalues: (ref 1): p_u_60, (copy 2): v_u_64 ]]
                        if p_u_60.Character:FindFirstChild("Animator") == nil then
                            Instance.new("Animator").Parent = v_u_64
                        end;
                        v_u_64:SetStateEnabled(Enum.HumanoidStateType.FallingDown, false)
                        v_u_64:SetStateEnabled(Enum.HumanoidStateType.Ragdoll, false)
                    end)
                    if p_u_61 == true then
                        local v65 = p_u_62 + Vector3.new(0, 0.75, 0)
                        if p_u_60.Character and p_u_60.Character.PrimaryPart then
                            p_u_60.Character:SetPrimaryPartCFrame(v65)
                        elseif l_RootPart_0 then
                            l_RootPart_0.CFrame = v65
                        end;
                    else
                        p_u_62 = v_u_36:get_random_cframe()
                        local v66 = v_u_5:get_randomized_character_position(p_u_62.p, p_u_62.p + p_u_62.LookVector, 5, 5, 0.5)
                        p_u_62 = CFrame.lookAt(v66, v66 + p_u_62.LookVector)
                        if p_u_60.Character and p_u_60.Character.PrimaryPart then
                            p_u_60.Character:SetPrimaryPartCFrame(p_u_62)
                        elseif l_RootPart_0 then
                            l_RootPart_0.CFrame = p_u_62
                        end;
                    end;
                    p_u_59:cache_player_character_cframe(p_u_60.UserId)
                    p_u_40._player_model_cache:parent_player_character(p_u_60)
                    p_u_40._player_manager._character_collide_group:add_to_group(p_u_60.Character)
                    l_RootPart_0.Anchored = false
                    local v67 = p_u_40._player_blob_manager:get_cached_blob(v_u_63)
                    if v67 ~= nil then
                        v_u_7:character_modify_with_equipped_data(p_u_60.Character, p_u_40._player_model_cache:get_cached_player_model(p_u_60), v_u_6:playerblob_get_equipped_info(v67))
                        v_u_8:err_if_banned(v67)
                    end;
                    p_u_40._evt:fire_event_to_client(v_u_4.EVT_Lobby_ServerAcknowledgeClientEnter, p_u_60, {
                        ["CharacterGroupID"] = v_u_14:get_player_collision_group():get_character_group_id(),
                        ["TransparentGroupID"] = v_u_14:get_player_collision_group():get_transparent_group_id(),
                        ["HUDNotifications"] = v_u_19:list_to_table(v_u_18:rbxid_get_notification_list(v_u_63))
                    })
                    p_u_40._player_status_manager:send_player_lobby_load_event(v_u_63)
                    f_player_blob_get_info(v67, function(p68) --[[ Line: 197 ]]
                        --[[ Upvalues: (ref 1): p_u_40, (ref 2): v_u_4, (ref 3): v_u_63, (ref 4): p_u_60 ]]
                        for _, v69 in p_u_40._player_manager:players_key_itr() do
                            p_u_40._evt:fire_event_to_client(v_u_4.EVT_Lobby_ServerNotifyAllPlayerEnteredLobby, v69, v_u_63, p68, p_u_60.Character)
                        end;
                    end)
                    v_u_58:on_player_spawned_to_lobby(p_u_60, p_u_60.Character)
                end)
            end)
            p_u_40._evt:wait_on_event(v_u_4.EVT_Lobby_ClientRequestPlayerInfoList, function(p_u_70, p71) --[[ Line: 207 ]]
                --[[ Upvalues: (ref 1): v_u_16, (ref 2): p_u_40, (ref 3): v_u_4, (ref 4): f_player_blob_get_info ]]
                local v_u_72 = {}
                local v_u_73 = v_u_16:new(#p71, function() --[[ Line: 209 ]]
                    --[[ Upvalues: (ref 1): p_u_40, (ref 2): v_u_4, (copy 3): p_u_70, (copy 4): v_u_72 ]]
                    p_u_40._evt:fire_event_to_client(v_u_4.EVT_Lobby_ServerResponseRequestPlayerInfoList, p_u_70, v_u_72)
                end)
                for v74 = 1, #p71 do
                    f_player_blob_get_info(p_u_40._player_blob_manager:get_cached_blob(p71[v74]), function(p75) --[[ Line: 215 ]]
                        --[[ Upvalues: (copy 1): v_u_72, (copy 2): v_u_73 ]]
                        v_u_72[#v_u_72 + 1] = p75
                        v_u_73:finish()
                    end)
                end;
            end)
            p_u_40._evt:wait_on_event(v_u_4.EVT_Lobby_ClientNotifyLeavingLobby, function(p76) --[[ Line: 222 ]]
                --[[ Upvalues: (copy 1): p_u_59, (ref 2): p_u_40, (ref 3): v_u_4 ]]
                p_u_59:cache_player_character_cframe(p76.UserId)
                p_u_40._player_model_cache:store_player_lobby_character(p76)
                for v77, v78 in p_u_40._player_manager:players_key_itr() do
                    if v77 ~= p76.UserId then
                        p_u_40._evt:fire_event_to_client(v_u_4.EVT_Lobby_ServerNotifyOthersLeavingLobby, v78, p76.UserId)
                    end;
                end;
            end)
            p_u_40._evt:wait_on_event(v_u_4.EVT_Lobby_ClientNotifyCharacterUpdateEquipped, function(p_u_79, p80, p_u_81, p82, p83) --[[ Line: 237 ]]
                --[[ Upvalues: (ref 1): p_u_40, (ref 2): v_u_4, (ref 3): v_u_5, (ref 4): v_u_56, (ref 5): v_u_1, (ref 6): v_u_6, (ref 7): v_u_24, (ref 8): v_u_12, (copy 9): p_u_59, (ref 10): v_u_51, (ref 11): v_u_52, (ref 12): v_u_11, (ref 13): v_u_8 ]]
                local function f_response(p84, p85) --[[ Name: response ]] --[[ Line: 238 ]]
                    --[[ Upvalues: (ref 1): p_u_40, (ref 2): v_u_4, (copy 3): p_u_79 ]]
                    return p_u_40._evt:fire_event_to_client(v_u_4.EVT_Lobby_ServerAcknowledgeCharacterUpdateEquipped, p_u_79, p84, p85);
                end;
                local v86 = v_u_5:get_player_id(p_u_79)
                if v_u_56:is_on_cooldown(v86) == true then
                    v_u_1:warnf("EVT_Lobby_ClientNotifyCharacterUpdateEquipped player(%s) on cooldown", (tostring(v86)))
                    return f_response(false, "on cooldown");
                end;
                v_u_56:add_cooldown_to_id(v86, 1)
                local v_u_87 = p_u_40._player_blob_manager:get_cached_blob(v86)
                if v_u_87 == nil then
                    return f_response(false, "cannot find playerblob");
                end;
                if v_u_6:playerblob_validate_equippedlist(v_u_87, p80) ~= true then
                    return f_response(false, "invalid equipped list");
                end;
                if v_u_24:playerblob_validate_equipped_pet_table(v_u_87, p82) ~= true then
                    return f_response(false, "invalid pet equipped list");
                end;
                local v_u_88 = nil
                if pcall(function() --[[ Line: 255 ]]
                    --[[ Upvalues: (ref 1): v_u_88, (ref 2): v_u_12, (copy 3): v_u_87, (copy 4): p_u_81 ]]
                    v_u_88 = v_u_12:playerblob_validate_loadouts_table_and_convert_to_id_to_loadout_dict(v_u_87, p_u_81)
                end) ~= true then
                    return f_response(false, "invalid loadouts");
                end;
                if v_u_88 == nil then
                    return f_response(false, "id_to_loadout_dict nil");
                end;
                v_u_6:set_equippedlist(v_u_87, p80)
                v_u_12:playerblob_write_id_to_loadout_dict(v_u_87, v_u_88)
                v_u_24:playerblob_write_equipped_pet_table(v_u_87, p82)
                local function v89() --[[ Line: 265 ]]
                    --[[ Upvalues: (ref 1): p_u_59, (copy 2): p_u_79, (copy 3): v_u_87 ]]
                    p_u_59:update_player_character_to_equipped_data(p_u_79, v_u_87)
                end;
                if v_u_51:contains(v86) then
                    v_u_52:add(v86, v89)
                else
                    p_u_59:update_player_character_to_equipped_data(p_u_79, v_u_87)
                    v_u_51:add(v86, v_u_11.SERVER_UPDATE_EQUIPPED_COOLDOWN_SEC)
                end;
                if p83 ~= true then
                    return f_response(true, "");
                end;
                p_u_40._player_blob_manager:enqueue_blob_sync_request(v86, v_u_8.PlayerBlobRequestType.Write, function(_) --[[ Line: 279 ]]
                    --[[ Upvalues: (copy 1): f_response ]]
                    return f_response(true, "");
                end)
            end)
            p_u_40._evt:wait_on_event(v_u_4.EVT_Lobby_ClientRequestDeleteGear, function(p_u_90, p91) --[[ Line: 288 ]]
                --[[ Upvalues: (ref 1): p_u_40, (ref 2): v_u_4, (ref 3): v_u_6, (ref 4): v_u_12, (ref 5): v_u_8 ]]
                local function f_response(p92, p93) --[[ Name: response ]] --[[ Line: 289 ]]
                    --[[ Upvalues: (ref 1): p_u_40, (ref 2): v_u_4, (copy 3): p_u_90 ]]
                    p_u_40._evt:fire_event_to_client(v_u_4.EVT_Lobby_ServerResponseDeleteGear, p_u_90, p92, p93)
                end;
                local v94 = p_u_40._player_blob_manager:get_cached_blob(p_u_90.UserId)
                if v94 == nil then
                    return f_response(false, "Playerblob nil");
                end;
                if v_u_6:ownedid_is_equipped(v94, p91) then
                    return f_response(false, "Cannot trash equipped gear.");
                end;
                if v_u_6:playerblob_ownedid_to_equipmentid(v94, p91) == nil then
                    return f_response(false, "Cannot find equipmentid for ownedid.");
                end;
                v_u_12:remove_ownedid_from_loadouts(v94, p91)
                v_u_6:playerblob_delete_ownedid(v94, p91)
                p_u_40._player_blob_manager:enqueue_blob_sync_request(p_u_90.UserId, v_u_8.PlayerBlobRequestType.Write, function(_) --[[ Line: 303 ]]
                    --[[ Upvalues: (ref 1): p_u_40, (ref 2): v_u_4, (copy 3): p_u_90 ]]
                    p_u_40._evt:fire_event_to_client(v_u_4.EVT_Lobby_ServerResponseDeleteGear, p_u_90, true, "Success")
                end)
            end)
            p_u_40._evt:wait_on_event(v_u_4.EVT_Lobby_ClientRequestSyncDanceToPlayer, function(p95, p96) --[[ Line: 309 ]]
                --[[ Upvalues: (ref 1): p_u_40, (ref 2): v_u_53, (ref 3): v_u_5, (ref 4): v_u_4, (ref 5): v_u_25 ]]
                local v97 = p_u_40._player_manager:id_to_player(p96)
                if v97 == nil then
                    return;
                elseif v_u_53:is_on_cooldown(p95.UserId) ~= true then
                    v_u_53:add_cooldown_to_id(p95.UserId, 0.5)
                    local v_u_98 = v_u_5:get_player_animator(v97)
                    local v_u_99 = v_u_5:get_player_animator(p95)
                    if v_u_99 and v_u_98 then
                        for _, v100 in p_u_40._player_manager:players_key_itr() do
                            p_u_40._evt:fire_event_to_client(v_u_4.EVT_Lobby_ServerNotifySyncDanceToPlayer, v100, p95.UserId, p96)
                        end;
                        spawn(function() --[[ Line: 326 ]]
                            --[[ Upvalues: (copy 1): v_u_98, (copy 2): v_u_99, (ref 3): v_u_25 ]]
                            if v_u_98 ~= nil and v_u_99 ~= nil then
                                for _, v101 in pairs(v_u_98:GetPlayingAnimationTracks()) do
                                    for _, v102 in pairs(v_u_99:GetPlayingAnimationTracks()) do
                                        if v101.Animation and (v102.Animation and (v101.Animation.AnimationId == v102.Animation.AnimationId and v_u_25:singleton():assetid_is_dance(v102.Animation.AnimationId))) then
                                            v102.TimePosition = v101.TimePosition
                                        end;
                                    end;
                                end;
                            end;
                        end)
                    end;
                end;
            end)
            p_u_40._evt:wait_on_event(v_u_4.EVT_StartupFetchMiscData, function(p_u_103) --[[ Line: 344 ]]
                --[[ Upvalues: (ref 1): p_u_40, (ref 2): v_u_4, (ref 3): v_u_35 ]]
                p_u_40._datastore_api:get_favorite_songs_data(p_u_103.UserId, function(_, p104) --[[ Line: 345 ]]
                    --[[ Upvalues: (ref 1): p_u_40, (ref 2): v_u_4, (copy 3): p_u_103 ]]
                    p_u_40._evt:fire_event_to_client(v_u_4.EVT_FavoriteData_ServerResponse, p_u_103, p104:to_table())
                end)
                p_u_40._datastore_api:get_playerid_liked_web_npc_ids_set(p_u_103.UserId, function(p105) --[[ Line: 349 ]]
                    --[[ Upvalues: (ref 1): p_u_40, (ref 2): v_u_4, (copy 3): p_u_103 ]]
                    p_u_40._evt:fire_event_to_client(v_u_4.EVT_WebNPC_ServerSendLikedWebNPCSet, p_u_103, p105:key_list():get_table())
                end)
                v_u_35:datastore_get_player_assignment_data(p_u_40, p_u_103.UserId, function(p106) --[[ Line: 353 ]]
                    --[[ Upvalues: (ref 1): p_u_40, (ref 2): v_u_4, (copy 3): p_u_103 ]]
                    p_u_40._evt:fire_event_to_client(v_u_4.EVT_PetAssignment_ServerPushData, p_u_103, p106:to_table())
                end)
            end)
            local v_u_107 = v_u_32:new()
            p_u_40._evt:wait_on_event(v_u_4.EVT_FavoriteData_ClientAddSong, function(p_u_108, p_u_109) --[[ Line: 360 ]]
                --[[ Upvalues: (ref 1): v_u_22, (ref 2): v_u_21, (copy 3): v_u_107, (ref 4): p_u_40, (ref 5): v_u_4, (ref 6): v_u_20 ]]
                v_u_22:is_true(v_u_21:singleton():contains_key(p_u_109))
                v_u_107:queue_key_request(p_u_108.UserId, function() --[[ Line: 362 ]]
                    --[[ Upvalues: (ref 1): p_u_40, (ref 2): v_u_4, (copy 3): p_u_108, (ref 4): v_u_21, (copy 5): p_u_109, (ref 6): v_u_20 ]]
                    local function f_response(p110, p111, p112) --[[ Name: response ]] --[[ Line: 363 ]]
                        --[[ Upvalues: (ref 1): p_u_40, (ref 2): v_u_4, (ref 3): p_u_108 ]]
                        p_u_40._evt:fire_event_to_client(v_u_4.EVT_FavoriteData_ServerAddSongResponse, p_u_108, p110, p111, p112)
                    end;
                    if v_u_21:singleton():get_songkey_priority(p_u_109) == v_u_21.SongPriority.Hidden then
                        return f_response(false, "Cannot add this song to favorites.", v_u_20:new(p_u_108.UserId):to_table());
                    end;
                    p_u_40._datastore_api:datastore_api_player_set_favorite_songs(p_u_108.UserId, p_u_109, function(p113, p114, p115) --[[ Line: 375 ]]
                        --[[ Upvalues: (copy 1): f_response ]]
                        if p113 == true then
                            return f_response(true, p114, p115:to_table());
                        else
                            return f_response(false, p114, p115:to_table());
                        end;
                    end)
                end)
            end)
            p_u_40._evt:wait_on_event(v_u_4.EVT_Lobby_ClientRequestIncreaseGearSlotLevel, function(p_u_116) --[[ Line: 390 ]]
                --[[ Upvalues: (ref 1): p_u_40, (ref 2): v_u_4, (ref 3): v_u_26, (ref 4): v_u_8, (ref 5): v_u_1, (ref 6): v_u_27 ]]
                local function f_response(p117, p118, p119) --[[ Name: response ]] --[[ Line: 391 ]]
                    --[[ Upvalues: (ref 1): p_u_40, (ref 2): v_u_4, (copy 3): p_u_116 ]]
                    p_u_40._evt:fire_event_to_client(v_u_4.EVT_Lobby_ServerResponseIncreaseGearSlotLevel, p_u_116, p117, p118, p119 == nil and {} or p119)
                end;
                p_u_40._player_blob_manager:get_verified_cached_blob(p_u_116.UserId, function(p120) --[[ Line: 396 ]]
                    --[[ Upvalues: (copy 1): f_response, (ref 2): v_u_26, (ref 3): v_u_8, (ref 4): v_u_1, (ref 5): v_u_27, (ref 6): p_u_40, (copy 7): p_u_116, (ref 8): v_u_4 ]]
                    if p120 == nil then
                        return f_response(false, "Playerblob nil");
                    end;
                    if v_u_26:can_playerblob_increase_level(p120) ~= true then
                        return f_response(false, "Cannot increase maximum number of gear any further.");
                    end;
                    local v121, v122 = v_u_26:get_currency_to_next_level(v_u_26:playerblob_get_gear_slot_increase_level(p120))
                    local v123 = v_u_8:get_currency_type_amount(p120, v122)
                    if v123 < v121 then
                        return f_response(false, string.format("Not enough %s to increase maximum number of gear.", v_u_8:currency_type_to_string(v122)));
                    end;
                    v_u_8:set_currency_type_amount(p120, v122, v123 - v121)
                    if v_u_26:playerblob_do_increment_max_gear_slot_level(p120) == false then
                        return v_u_1:errf("EVT_Lobby_ClientRequestIncreaseGearSlotLevel playerblob_do_increment_max_gear_slot_level failed");
                    end;
                    v_u_27:server_sync_reward_params(p_u_40, p_u_116, v_u_27:claim_reward_info_list_to_playerblob(p_u_40, p120, (v_u_26:playerblob_get_available_reward_desc_info_list(p120))), function(p124, _, p125) --[[ Line: 423 ]]
                        --[[ Upvalues: (ref 1): v_u_27, (ref 2): p_u_40, (ref 3): v_u_4, (ref 4): p_u_116 ]]
                        local v126 = v_u_27.RewardInfo:list_to_table(p125)
                        p_u_40._evt:fire_event_to_client(v_u_4.EVT_Lobby_ServerResponseIncreaseGearSlotLevel, p_u_116, true, p124, v126 == nil and {} or v126)
                    end)
                end)
            end)
            p_u_40._evt:wait_on_event(v_u_4.EVT_Lobby_ClientNotifyEnterSettings, function(p127, p128) --[[ Line: 430 ]]
                --[[ Upvalues: (ref 1): v_u_22, (ref 2): v_u_21, (ref 3): p_u_40 ]]
                v_u_22:is_true(v_u_21:singleton():contains_key(p128))
                p_u_40._player_status_manager:send_player_in_settings_event(p127.UserId, p128)
            end)
            p_u_40._evt:wait_on_event(v_u_4.EVT_Lobby_ClientRequestIncreaseLoadoutLevel, function(p_u_129) --[[ Line: 435 ]]
                --[[ Upvalues: (ref 1): p_u_40, (ref 2): v_u_4, (ref 3): v_u_12, (ref 4): v_u_8, (ref 5): v_u_1, (ref 6): v_u_26, (ref 7): v_u_27, (ref 8): v_u_9 ]]
                local function f_response(p130, p131, p132) --[[ Name: response ]] --[[ Line: 436 ]]
                    --[[ Upvalues: (ref 1): p_u_40, (ref 2): v_u_4, (copy 3): p_u_129 ]]
                    p_u_40._evt:fire_event_to_client(v_u_4.EVT_Lobby_ServerResponseIncreaseLoadoutLevel, p_u_129, p130, p131, p132 == nil and {} or p132)
                end;
                p_u_40._player_blob_manager:get_verified_cached_blob(p_u_129.UserId, function(p_u_133) --[[ Line: 441 ]]
                    --[[ Upvalues: (copy 1): f_response, (ref 2): v_u_12, (ref 3): v_u_8, (ref 4): v_u_1, (ref 5): v_u_26, (ref 6): v_u_27, (ref 7): p_u_40, (copy 8): p_u_129, (ref 9): v_u_4, (ref 10): v_u_9 ]]
                    if p_u_133 == nil then
                        return f_response(false, "Playerblob nil");
                    end;
                    if v_u_12:can_playerblob_upgrade_loadout_slot_level(p_u_133) ~= true then
                        return f_response(false, "Cannot increase maximum number of loadouts any further.");
                    end;
                    local v134, v135 = v_u_12:playerblob_get_next_loadout_slot_level_price(p_u_133)
                    local v136 = v_u_8:get_currency_type_amount(p_u_133, v135)
                    if v136 < v134 then
                        return f_response(false, string.format("Not enough %s to increase maximum number of loadouts.", v_u_8:currency_type_to_string(v135)));
                    end;
                    v_u_8:set_currency_type_amount(p_u_133, v135, v136 - v134)
                    if v_u_12:playerblob_do_increment_loadout_slot_level(p_u_133) == false then
                        return v_u_1:errf("EVT_Lobby_ClientRequestIncreaseLoadoutLevel playerblob_do_increment_loadout_slot_level failed");
                    end;
                    v_u_27:server_sync_reward_params(p_u_40, p_u_129, v_u_27:claim_reward_info_list_to_playerblob(p_u_40, p_u_133, (v_u_26:playerblob_get_available_reward_desc_info_list(p_u_133))), function(p137, _, p138) --[[ Line: 468 ]]
                        --[[ Upvalues: (ref 1): v_u_27, (ref 2): p_u_40, (ref 3): v_u_4, (ref 4): p_u_129, (ref 5): v_u_9, (ref 6): v_u_12, (copy 7): p_u_133 ]]
                        local v139 = v_u_27.RewardInfo:list_to_table(p138)
                        p_u_40._evt:fire_event_to_client(v_u_4.EVT_Lobby_ServerResponseIncreaseLoadoutLevel, p_u_129, true, p137, v139 == nil and {} or v139)
                        p_u_40._api:api_report_evt(v_u_9.ReportEvt_PlayerLoadoutSlotIncreasePurchase, p_u_129.UserId, v_u_12:playerblob_get_loadout_slot_level(p_u_133), "")
                    end)
                end)
            end)
            p_u_40._evt:wait_on_event(v_u_4.EVT_Lobby_ClientRequestLoadoutNameChanged, function(p_u_140, p_u_141, p_u_142) --[[ Line: 484 ]]
                --[[ Upvalues: (ref 1): v_u_22, (ref 2): p_u_40, (ref 3): v_u_4, (ref 4): v_u_12, (ref 5): v_u_5, (ref 6): v_u_28, (ref 7): v_u_8, (ref 8): v_u_1 ]]
                v_u_22:is_int(p_u_141)
                v_u_22:is_string(p_u_142)
                local function f_response(p143, p144) --[[ Name: response ]] --[[ Line: 488 ]]
                    --[[ Upvalues: (ref 1): p_u_40, (ref 2): v_u_4, (copy 3): p_u_140 ]]
                    p_u_40._evt:fire_event_to_client(v_u_4.EVT_Lobby_ServerResponseLoadoutNameChanged, p_u_140, p143, p144)
                end;
                p_u_40._player_blob_manager:get_verified_cached_blob(p_u_140.UserId, function(p_u_145) --[[ Line: 492 ]]
                    --[[ Upvalues: (copy 1): f_response, (copy 2): p_u_142, (ref 3): v_u_12, (copy 4): p_u_141, (ref 5): v_u_5, (copy 6): p_u_140, (ref 7): p_u_40, (ref 8): v_u_28, (ref 9): v_u_8, (ref 10): v_u_1 ]]
                    if p_u_145 == nil then
                        return f_response(false, "Playerblob nil");
                    end;
                    if #p_u_142 > v_u_12:max_loadout_name_length() then
                        return f_response(false, "Loadout name too long.");
                    end;
                    if v_u_12:get_loadout_index_range(p_u_145):contains_eq(p_u_141) ~= true then
                        return f_response(false, "Invalid loadout id.");
                    end;
                    spawn(function() --[[ Line: 497 ]]
                        --[[ Upvalues: (ref 1): v_u_5, (ref 2): p_u_142, (ref 3): p_u_140, (ref 4): p_u_40, (ref 5): v_u_28, (ref 6): v_u_8, (copy 7): p_u_145, (ref 8): v_u_12, (ref 9): p_u_141, (ref 10): v_u_1, (ref 11): f_response ]]
                        local v_u_146 = v_u_5:filter_string(p_u_142, p_u_140, p_u_140)
                        p_u_40._post_fn:enqueue_function(function() --[[ Line: 499 ]]
                            --[[ Upvalues: (ref 1): v_u_28, (ref 2): v_u_8, (ref 3): p_u_145, (ref 4): v_u_12, (ref 5): p_u_141, (copy 6): v_u_146, (ref 7): v_u_5, (ref 8): v_u_1, (ref 9): p_u_40, (ref 10): p_u_140, (ref 11): f_response ]]
                            local v147 = v_u_28:new()
                            v147:load_from_json_str(v_u_8:get_player_settings_str(p_u_145))
                            v_u_12:write_playerblob_loadout_index_name_to_settings(p_u_145, p_u_141, v_u_146, v147)
                            if v_u_5:is_dev_build() then
                                v_u_1:puts(v_u_5:table_to_string(v147:get_key(v_u_28.Key.LoadoutNames)))
                            end;
                            v_u_8:set_player_settings_str(p_u_145, v147:to_json())
                            p_u_40._player_blob_manager:enqueue_blob_sync_request(p_u_140.UserId, v_u_8.PlayerBlobRequestType.Write, function(_) --[[ Line: 513 ]]
                                --[[ Upvalues: (ref 1): f_response ]]
                                return f_response(true, "");
                            end)
                        end)
                    end)
                end)
            end)
            local function f_generic_message_board_category_to_key(p148, p149) --[[ Name: generic_message_board_category_to_key ]] --[[ Line: 522 ]]
                --[[ Upvalues: (ref 1): v_u_30, (ref 2): p_u_40, (ref 3): v_u_33, (ref 4): v_u_1 ]]
                local function f_weekly_leaderboard_key_for_weekid(p150) --[[ Name: weekly_leaderboard_key_for_weekid ]] --[[ Line: 523 ]]
                    return string.format("weekly_leaderboard_%d", p150);
                end;
                local function f_weekly_guild_contribution_leaderboard_key_for_weekid(p151) --[[ Name: weekly_guild_contribution_leaderboard_key_for_weekid ]] --[[ Line: 526 ]]
                    return string.format("weekly_guild_cntr_lb_%d", p151);
                end;
                local function f_weekly_mission_leaderboard_key_for_weekid(p152) --[[ Name: weekly_mission_leaderboard_key_for_weekid ]] --[[ Line: 529 ]]
                    return string.format("weekly_mission_lb_%d", p152);
                end;
                if p148 == v_u_30.Category.CurrentWeeklyLeaderboard then
                    return f_weekly_leaderboard_key_for_weekid(p_u_40._api:get_week_id());
                elseif p148 == v_u_30.Category.LastWeeklyLeaderboard then
                    return f_weekly_leaderboard_key_for_weekid(p_u_40._api:get_week_id() - 1);
                elseif p148 == v_u_30.Category.CurrentGuildContributionWeeklyLeaderboard then
                    return f_weekly_guild_contribution_leaderboard_key_for_weekid(p_u_40._api:get_week_id());
                elseif p148 == v_u_30.Category.LastGuildContributionWeeklyLeaderboard then
                    return f_weekly_guild_contribution_leaderboard_key_for_weekid(p_u_40._api:get_week_id() - 1);
                elseif p148 == v_u_30.Category.CurrentWeeklyMissionLeaderboard then
                    return f_weekly_mission_leaderboard_key_for_weekid(p_u_40._api:get_week_id());
                elseif p148 == v_u_30.Category.LastWeeklyMissionLeaderboard then
                    return f_weekly_mission_leaderboard_key_for_weekid(p_u_40._api:get_week_id() - 1);
                elseif p148 == v_u_30.Category.CustomMap then
                    if v_u_33:validate_custom_map_key_components(p149) == true then
                        return string.format("cmap_%s", p149);
                    else
                        return v_u_1:errf("Invalid custom map key components: %s", (tostring(p149)));
                    end;
                else
                    return string.format("category_%s", (tostring(p148)));
                end;
            end;
            p_u_40._evt:wait_on_event(v_u_4.EVT_Lobby_GetGenericMessageBoardClient, function(p_u_153, p154, p155) --[[ Line: 555 ]]
                --[[ Upvalues: (ref 1): v_u_22, (ref 2): v_u_30, (ref 3): p_u_40, (ref 4): v_u_4, (ref 5): v_u_29, (copy 6): f_generic_message_board_category_to_key ]]
                v_u_22:is_enum_member(p154, v_u_30.Category)
                local function _(p156) --[[ Name: response ]] --[[ Line: 558 ]]
                    --[[ Upvalues: (ref 1): p_u_40, (ref 2): v_u_4, (copy 3): p_u_153, (ref 4): v_u_29 ]]
                    p_u_40._evt:fire_event_to_client(v_u_4.EVT_Lobby_GetGenericMessageBoardServerResponse, p_u_153, v_u_29:list_to_table(p156))
                end;
                p_u_40._datastore_api:get_key_message_board_messages(f_generic_message_board_category_to_key(p154, p155), function(p157) --[[ Line: 562 ]]
                    --[[ Upvalues: (ref 1): p_u_40, (ref 2): v_u_4, (copy 3): p_u_153, (ref 4): v_u_29 ]]
                    p_u_40._evt:fire_event_to_client(v_u_4.EVT_Lobby_GetGenericMessageBoardServerResponse, p_u_153, v_u_29:list_to_table(p157))
                end)
            end)
            local v_u_158 = v_u_32:new():set_cooldown(5)
            p_u_40._evt:wait_on_event(v_u_4.EVT_Lobby_PostGenericMessageClient, function(p_u_159, p_u_160, p_u_161, p_u_162) --[[ Line: 569 ]]
                --[[ Upvalues: (ref 1): v_u_22, (ref 2): v_u_30, (copy 3): v_u_158, (ref 4): v_u_2, (ref 5): p_u_40, (ref 6): v_u_4, (ref 7): v_u_29, (ref 8): v_u_55, (ref 9): v_u_5, (copy 10): f_generic_message_board_category_to_key, (ref 11): v_u_31, (ref 12): v_u_8 ]]
                v_u_22:is_enum_member(p_u_160, v_u_30.Category)
                v_u_22:is_string(p_u_162)
                v_u_158:queue_key_request(p_u_159.UserId, function() --[[ Line: 572 ]]
                    --[[ Upvalues: (ref 1): v_u_2, (ref 2): p_u_40, (ref 3): v_u_4, (copy 4): p_u_159, (ref 5): v_u_29, (ref 6): v_u_55, (ref 7): v_u_5, (copy 8): p_u_162, (ref 9): f_generic_message_board_category_to_key, (copy 10): p_u_160, (copy 11): p_u_161, (ref 12): v_u_31, (ref 13): v_u_8 ]]
                    local function f_response(p163, p164, p165, p166) --[[ Name: response ]] --[[ Line: 573 ]]
                        --[[ Upvalues: (ref 1): v_u_2, (ref 2): p_u_40, (ref 3): v_u_4, (ref 4): p_u_159, (ref 5): v_u_29 ]]
                        if p165 == nil then
                            p165 = v_u_2:new()
                        end;
                        if p166 == nil then
                            p166 = false
                        end;
                        p_u_40._evt:fire_event_to_client(v_u_4.EVT_Lobby_PostGenericMessageServerResponse, p_u_159, p163, p164, v_u_29:list_to_table(p165), p166)
                    end;
                    if v_u_55:is_on_cooldown(p_u_159.UserId) then
                        return f_response(false, "Posting Message on cooldown");
                    end;
                    spawn(function() --[[ Line: 580 ]]
                        --[[ Upvalues: (ref 1): v_u_5, (ref 2): p_u_162, (ref 3): p_u_159, (copy 4): f_response, (ref 5): p_u_40, (ref 6): v_u_55, (ref 7): f_generic_message_board_category_to_key, (ref 8): p_u_160, (ref 9): p_u_161, (ref 10): v_u_29, (ref 11): v_u_31, (ref 12): v_u_8 ]]
                        local v_u_167 = v_u_5:filter_string(p_u_162, p_u_159, p_u_159)
                        if v_u_167 ~= p_u_162 then
                            return f_response(false, string.format("Message did not pass roblox moderation(%s)", v_u_167));
                        end;
                        p_u_40._post_fn:enqueue_function(function() --[[ Line: 585 ]]
                            --[[ Upvalues: (ref 1): v_u_55, (ref 2): p_u_159, (ref 3): p_u_40, (ref 4): f_generic_message_board_category_to_key, (ref 5): p_u_160, (ref 6): p_u_161, (ref 7): v_u_29, (copy 8): v_u_167, (ref 9): v_u_31, (ref 10): f_response, (ref 11): v_u_8 ]]
                            v_u_55:add_cooldown_to_id(p_u_159.UserId, 2.5)
                            p_u_40._datastore_api:write_key_message_board_message(f_generic_message_board_category_to_key(p_u_160, p_u_161), v_u_29:new():set_player_id_name(p_u_159.UserId, p_u_159.Name):set_message_time(p_u_40._api:get_global_time()):set_message_text(v_u_167), function(p_u_168) --[[ Line: 594 ]]
                                --[[ Upvalues: (ref 1): v_u_31, (ref 2): p_u_40, (ref 3): p_u_159, (ref 4): f_response, (ref 5): v_u_8 ]]
                                if v_u_31:can_claim_daily_mission_type_playerblob_dayid_monthid(v_u_31.DailyMissionType.PostTeamMessageBoard, p_u_40._player_blob_manager:get_cached_blob(p_u_159.UserId), p_u_40._api:get_day_id(), p_u_40._api:get_month_id()) ~= true then
                                    return f_response(true, "", p_u_168);
                                end;
                                p_u_40._player_blob_manager:get_verified_cached_blob(p_u_159.UserId, function(p169) --[[ Line: 596 ]]
                                    --[[ Upvalues: (ref 1): f_response, (copy 2): p_u_168, (ref 3): p_u_40, (ref 4): v_u_31, (ref 5): p_u_159, (ref 6): v_u_8 ]]
                                    if p169 == nil then
                                        return f_response(true, "", p_u_168);
                                    end;
                                    p_u_40._challengepass_manager:challengepassv2_daily_mission_playerblob_claim(v_u_31.DailyMissionType.PostTeamMessageBoard, p169)
                                    p_u_40._player_blob_manager:enqueue_blob_sync_request(p_u_159.UserId, v_u_8.PlayerBlobRequestType.Write, function(_) --[[ Line: 603 ]]
                                        --[[ Upvalues: (ref 1): f_response, (ref 2): p_u_168 ]]
                                        return f_response(true, "", p_u_168, true);
                                    end)
                                end)
                            end)
                        end)
                    end)
                end)
            end)
        end;
        local function f_perform_update_player_character_to_equipped_data(p170, p171) --[[ Name: perform_update_player_character_to_equipped_data ]] --[[ Line: 621 ]]
            --[[ Upvalues: (copy 1): p_u_40, (ref 2): v_u_7, (ref 3): v_u_6, (copy 4): v_u_58 ]]
            if p170 == nil then
                return;
            else
                local l_Character_0 = p170.Character
                local v172 = p_u_40._player_model_cache:get_cached_player_model(p170)
                if l_Character_0 ~= nil and v172 ~= nil then
                    v_u_7:character_modify_with_equipped_data(l_Character_0, v172, v_u_6:playerblob_get_equipped_info(p171))
                    v_u_58:on_player_reset(p170, l_Character_0)
                end;
            end;
        end;
        v41.update_player_character_to_equipped_data = function(_, p_u_173, p_u_174) --[[ Name: update_player_character_to_equipped_data ]] --[[ Line: 636 ]]
            --[[ Upvalues: (copy 1): f_perform_update_player_character_to_equipped_data, (copy 2): v_u_51, (copy 3): v_u_52, (ref 4): v_u_11 ]]
            local l_UserId_0 = p_u_173.UserId
            local function v175() --[[ Line: 638 ]]
                --[[ Upvalues: (ref 1): f_perform_update_player_character_to_equipped_data, (copy 2): p_u_173, (copy 3): p_u_174 ]]
                f_perform_update_player_character_to_equipped_data(p_u_173, p_u_174)
            end;
            if v_u_51:contains(l_UserId_0) then
                v_u_52:add(l_UserId_0, v175)
            else
                f_perform_update_player_character_to_equipped_data(p_u_173, p_u_174)
                v_u_51:add(l_UserId_0, v_u_11.SERVER_UPDATE_EQUIPPED_COOLDOWN_SEC)
            end;
        end;
        v41.cache_player_character_cframe = function(_, p176) --[[ Name: cache_player_character_cframe ]] --[[ Line: 649 ]]
            --[[ Upvalues: (copy 1): p_u_40, (ref 2): v_u_5, (copy 3): v_u_57 ]]
            local v177 = p_u_40._player_manager:id_to_player(p176)
            if v177 == nil then
                return;
            elseif v177.Character ~= nil then
                local v178 = v_u_5:first_child_of_type(v177.Character, "Humanoid")
                if v178 and v178.RootPart then
                    v_u_57:add(p176, v178.RootPart.CFrame)
                end;
            end;
        end;
        v41.push_player_info_updated = function(_, p_u_179) --[[ Name: push_player_info_updated ]] --[[ Line: 659 ]]
            --[[ Upvalues: (copy 1): p_u_40, (copy 2): f_player_blob_get_info, (ref 3): v_u_4 ]]
            local v180 = p_u_40._player_blob_manager:get_cached_blob(p_u_179)
            if v180 ~= nil then
                f_player_blob_get_info(v180, function(p181) --[[ Line: 662 ]]
                    --[[ Upvalues: (ref 1): p_u_40, (ref 2): v_u_4, (copy 3): p_u_179 ]]
                    for _, v182 in p_u_40._player_manager:players_key_itr() do
                        p_u_40._evt:fire_event_to_client(v_u_4.EVT_Lobby_ServerPushPlayerInfoUpdated, v182, p_u_179, p181)
                    end;
                end)
            end;
        end;
        v41.get_playerid_cached_cframe = function(_, p183) --[[ Name: get_playerid_cached_cframe ]] --[[ Line: 670 ]]
            --[[ Upvalues: (copy 1): v_u_57 ]]
            if v_u_57:contains(p183) then
                return v_u_57:get(p183);
            else
                return CFrame.new();
            end;
        end;
        v41.player_disconnecting = function(_, p184) --[[ Name: player_disconnecting ]] --[[ Line: 678 ]]
            --[[ Upvalues: (copy 1): v_u_51, (copy 2): v_u_52, (copy 3): v_u_57 ]]
            v_u_51:remove(p184)
            v_u_52:remove(p184)
            v_u_57:remove(p184)
        end;
        local v_u_185 = v_u_2:new()
        v41.update = function(p186, p187) --[[ Name: update ]] --[[ Line: 685 ]]
            --[[ Upvalues: (copy 1): v_u_185, (copy 2): v_u_51, (ref 3): v_u_10, (copy 4): v_u_52, (copy 5): v_u_53, (copy 6): v_u_58, (copy 7): v_u_55, (copy 8): v_u_56 ]]
            v_u_185:clear()
            local v188 = v_u_185
            for v189, v190 in v_u_51:key_itr() do
                local v191 = v190 - v_u_10:TimescaleToDeltaTime(p187)
                v_u_51:add(v189, v191)
                if v191 <= 0 then
                    v188:push_back(v189)
                end;
            end;
            for v192 = 1, v188:count() do
                local v_u_193 = v188:get(v192)
                if v_u_52:contains(v_u_193) then
                    pcall(function() --[[ Line: 699 ]]
                        --[[ Upvalues: (ref 1): v_u_52, (copy 2): v_u_193 ]]
                        v_u_52:get(v_u_193)()
                    end)
                end;
                v_u_51:remove(v_u_193)
                v_u_52:remove(v_u_193)
            end;
            v_u_53:update(p187)
            p186:update_culling_sync(p187)
            v_u_58:update(p187)
            v_u_55:update(p187)
            v_u_56:update(p187)
        end;
        local v_u_194 = v_u_2:new()
        v41.update_culling_sync = function(_, p195) --[[ Name: update_culling_sync ]] --[[ Line: 717 ]]
            --[[ Upvalues: (copy 1): v_u_54, (copy 2): v_u_194, (copy 3): p_u_40, (copy 4): v_u_58, (ref 5): v_u_4, (ref 6): v_u_11 ]]
            v_u_54:update(p195)
            if v_u_54:is_on_cooldown() ~= true then
                v_u_194:clear()
                for _, v196 in p_u_40._player_manager:players_key_itr() do
                    local l_Character_1 = v196.Character
                    if l_Character_1 ~= nil and l_Character_1.PrimaryPart ~= nil then
                        v_u_194:push_back({
                            ["Character"] = l_Character_1,
                            ["CFrame"] = l_Character_1.PrimaryPart.CFrame
                        })
                    end;
                end;
                for _, v197 in v_u_58:get_active_follow_npcs():key_itr() do
                    local v198 = v197:get_npc_character()
                    if v198 ~= nil and v198.PrimaryPart ~= nil then
                        v_u_194:push_back({
                            ["Character"] = v198,
                            ["CFrame"] = v198.PrimaryPart.CFrame
                        })
                    end;
                end;
                for _, v199 in p_u_40._player_manager:players_key_itr() do
                    p_u_40._evt:fire_event_to_client(v_u_4.EVT_Lobby_ServerNotifySyncCullingDataToPlayer, v199, {
                        ["CharactersToSync"] = v_u_194:get_table()
                    })
                end;
                v_u_54:add_cooldown(v_u_11.SERVER_NOTIFY_SYNC_CULLING_DATA_TO_PLAYER_SEC)
            end;
        end;
        return v41;
    end
};
