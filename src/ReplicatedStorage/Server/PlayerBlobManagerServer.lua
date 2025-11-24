-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:13 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Server.DebugOut)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_5 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_6 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_7 = require(game.ReplicatedStorage.Server.ServerAPIManager)
local v_u_8 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_9 = require(game.ReplicatedStorage.Avatar.PlayerBlobAvatar)
local v_u_10 = require(game.ReplicatedStorage.Crafting.PlayerBlobCrafting)
require(game.ReplicatedStorage.Shared.MissionInfo)
local v_u_11 = require(game.ReplicatedStorage.Shared.PlayerSettings)
local v_u_12 = require(game.ReplicatedStorage.PlayerInfo.VIPInfo)
local v_u_13 = require(game.ReplicatedStorage.Avatar.PlayerBlobDance)
require(game.ReplicatedStorage.PlayerInfo.DanceDatabase)
local v_u_14 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_15 = require(game.ReplicatedStorage.Shared.Constants)
local v_u_16 = require(game.ReplicatedStorage.PlayerInfo.TitleDatabase)
local v_u_17 = require(game.ReplicatedStorage.PlayerInfo.PremiumRewardsInfo)
local v_u_18 = require(game.ReplicatedStorage.PlayerInfo.GroupRewardsInfo)
local v_u_19 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_20 = require(game.ReplicatedStorage.Shared.Mutex)
local v_u_21 = require(game.ReplicatedStorage.Shared.WaitForFinish)
local v_u_22 = require(game.ReplicatedStorage.Shared.GuildUtil)
local v_u_23 = require(game.ReplicatedStorage.Pets.PetUtils)
local v_u_24 = require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
local v_u_25 = require(game.ReplicatedStorage.PlayerInfo.LoginRewardUtil)
local v_u_26 = require(game.ReplicatedStorage.Shared.CooldownDelay)
local v_u_27 = require(game.ReplicatedStorage.Server.PlayerBlobDatastore.PlayerBlobDatastoreManager)
local v_u_28 = require(game.ReplicatedStorage.Server.PlayerBlobDatastore.PlayerBlobDatastoreComponent)
local v_u_29 = require(game.ReplicatedStorage.PlayerInfo.FeverIconDatabase)
local v_u_30 = require(game.ReplicatedStorage.PlayerInfo.ChallengePassUtils)
local v_u_31 = require(game.ReplicatedStorage.PlayerInfo.ChallengePassV2.ChallengePassV2Mission)
local s_HttpService_0 = game:GetService("HttpService")
local v32 = {}
local v_u_33 = {
    ["Get"] = 1,
    ["Write"] = 2,
    ["GetInitial"] = 3
}
v_u_8.PlayerBlobRequestType = v_u_33
local function _(p34) --[[ Name: is_request_type_get ]] --[[ Line: 46 ]]
    --[[ Upvalues: (copy 1): v_u_33 ]]
    return p34 == v_u_33.Get and true or p34 == v_u_33.GetInitial;
end;
local function _(p35) --[[ Name: is_request_type_write ]] --[[ Line: 49 ]]
    --[[ Upvalues: (copy 1): v_u_33 ]]
    return p35 == v_u_33.Write;
end;
local function _(p36, p37) --[[ Name: is_request_type_matching ]] --[[ Line: 52 ]]
    --[[ Upvalues: (copy 1): v_u_33 ]]
    return (p36 == v_u_33.Get or p36 == v_u_33.GetInitial) and (p37 == v_u_33.Get or p37 == v_u_33.GetInitial) and true or p36 == v_u_33.Write and p37 == v_u_33.Write;
end;
local v_u_51 = {
    ["new"] = function(_, p_u_38) --[[ Name: new ]] --[[ Line: 59 ]]
        --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_33, (copy 3): v_u_22, (copy 4): v_u_19 ]]
        local v39 = {}
        local v_u_40 = v_u_2:new()
        local l_Write_0 = v_u_33.Write
        local v_u_41 = v_u_22:not_in_guild_id()
        local v_u_42 = 0
        v39.get_user_id = function(_) --[[ Name: get_user_id ]] --[[ Line: 67 ]]
            --[[ Upvalues: (copy 1): p_u_38 ]]
            return p_u_38;
        end;
        v39.get_request_type = function(_) --[[ Name: get_request_type ]] --[[ Line: 68 ]]
            --[[ Upvalues: (ref 1): l_Write_0 ]]
            return l_Write_0;
        end;
        v39.has_guild_contribution = function(_) --[[ Name: has_guild_contribution ]] --[[ Line: 69 ]]
            --[[ Upvalues: (ref 1): v_u_41, (ref 2): v_u_22 ]]
            return v_u_41 ~= v_u_22:not_in_guild_id();
        end;
        v39.get_guild_contribution = function(_) --[[ Name: get_guild_contribution ]] --[[ Line: 70 ]]
            --[[ Upvalues: (ref 1): v_u_41, (ref 2): v_u_42 ]]
            return v_u_41, v_u_42;
        end;
        v39.set_request_type = function(p43, p44) --[[ Name: set_request_type ]] --[[ Line: 72 ]]
            --[[ Upvalues: (ref 1): v_u_19, (ref 2): v_u_33, (ref 3): l_Write_0 ]]
            v_u_19:is_enum_member(p44, v_u_33)
            l_Write_0 = p44
            return p43;
        end;
        v39.add_callback = function(p45, p46) --[[ Name: add_callback ]] --[[ Line: 78 ]]
            --[[ Upvalues: (copy 1): v_u_40 ]]
            v_u_40:push_back(p46)
            return p45;
        end;
        v39.get_callback_count = function(_) --[[ Name: get_callback_count ]] --[[ Line: 83 ]]
            --[[ Upvalues: (copy 1): v_u_40 ]]
            return v_u_40:count();
        end;
        v39.set_guild_contribution = function(_, p47, p48) --[[ Name: set_guild_contribution ]] --[[ Line: 87 ]]
            --[[ Upvalues: (ref 1): v_u_19, (ref 2): v_u_41, (ref 3): v_u_42 ]]
            v_u_19:is_int(p48)
            v_u_41 = p47
            v_u_42 = v_u_42 + p48
        end;
        v39.run_callbacks = function(_, p49) --[[ Name: run_callbacks ]] --[[ Line: 93 ]]
            --[[ Upvalues: (copy 1): v_u_40 ]]
            for v50 = 1, v_u_40:count() do
                v_u_40:get(v50)(p49)
            end;
            v_u_40:clear()
        end;
        return v39;
    end
}
v32.new = function(_, p_u_52) --[[ Name: new ]] --[[ Line: 104 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_2, (copy 3): v_u_26, (copy 4): v_u_27, (copy 5): v_u_15, (copy 6): v_u_1, (copy 7): v_u_33, (copy 8): v_u_6, (copy 9): v_u_20, (copy 10): v_u_19, (copy 11): v_u_21, (copy 12): v_u_5, (copy 13): s_HttpService_0, (copy 14): v_u_51, (copy 15): v_u_4, (copy 16): v_u_8, (copy 17): v_u_11, (copy 18): v_u_12, (copy 19): v_u_16, (copy 20): v_u_13, (copy 21): v_u_7, (copy 22): v_u_17, (copy 23): v_u_18, (copy 24): v_u_24, (copy 25): v_u_25, (copy 26): v_u_28, (copy 27): v_u_31, (copy 28): v_u_30, (copy 29): v_u_29, (copy 30): v_u_9, (copy 31): v_u_10, (copy 32): v_u_23, (copy 33): v_u_14 ]]
    local v_u_53 = {}
    local v_u_54 = v_u_3:new()
    local v_u_55 = v_u_3:new()
    local v_u_56 = v_u_3:new()
    local v_u_57 = v_u_2:new()
    local v_u_58 = v_u_26:new()
    local v_u_59 = v_u_27:new(p_u_52)
    v_u_53.get_cached_blob = function(_, p60) --[[ Name: get_cached_blob ]] --[[ Line: 116 ]]
        --[[ Upvalues: (copy 1): v_u_54 ]]
        if v_u_54:contains(p60) then
            return v_u_54:get(p60);
        else
            return nil;
        end;
    end;
    v_u_53.add_lock_to_player_id = function(_, p61) --[[ Name: add_lock_to_player_id ]] --[[ Line: 124 ]]
        --[[ Upvalues: (copy 1): v_u_54, (copy 2): v_u_56, (ref 3): v_u_15 ]]
        if v_u_54:contains(p61) then
            v_u_56:add(p61, v_u_15.SERVER_BLOB_LOCK_TIME_SEC)
        end;
    end;
    local function f_verify_playerblob(p62, p63, p_u_64) --[[ Name: verify_playerblob ]] --[[ Line: 130 ]]
        --[[ Upvalues: (copy 1): v_u_53, (copy 2): p_u_52, (ref 3): v_u_1, (ref 4): v_u_33 ]]
        local v65 = p63 == nil and true or p63
        local v66 = v_u_53:get_cached_blob(p62)
        if v66 == nil then
            p_u_64(nil, false)
            return;
        else
            v_u_53:add_lock_to_player_id(p62)
            local v67 = p_u_52._api:get_day_id()
            if v65 == true and v66.LastUpdatedDay ~= v67 then
                v_u_1:puts("PlayerBlobManagerServer verify_playerblob force_resync_get cached_blob.LastUpdatedDay(%s) ~= current_day_id(%s)", tostring(v66.LastUpdatedDay), (tostring(v67)))
                v_u_53:enqueue_blob_sync_request(p62, v_u_33.Get, function(p68) --[[ Line: 149 ]]
                    --[[ Upvalues: (copy 1): p_u_64 ]]
                    p_u_64(p68, true)
                end, true)
            else
                p_u_64(v66, false)
            end;
        end;
    end;
    local function _(p_u_69) --[[ Name: try_fn ]] --[[ Line: 157 ]]
        --[[ Upvalues: (ref 1): v_u_6, (copy 2): p_u_52 ]]
        local v70, v71 = v_u_6:try(function() --[[ Line: 158 ]]
            --[[ Upvalues: (copy 1): p_u_69 ]]
            p_u_69()
        end)
        if not v70 then
            p_u_52._error_report:evt_report_error(v71)
        end;
    end;
    local v_u_72 = v_u_20:new()
    v_u_53.is_player_id_verified_cached_blob_locked = function(_, p73) --[[ Name: is_player_id_verified_cached_blob_locked ]] --[[ Line: 167 ]]
        --[[ Upvalues: (copy 1): v_u_72 ]]
        return v_u_72:test(p73);
    end;
    v_u_53.get_verified_cached_blob = function(_, p_u_74, p_u_75, p76) --[[ Name: get_verified_cached_blob ]] --[[ Line: 172 ]]
        --[[ Upvalues: (ref 1): v_u_20, (copy 2): v_u_72, (copy 3): f_verify_playerblob, (ref 4): v_u_6, (copy 5): p_u_52 ]]
        local v_u_77 = p76 == nil and true or p76
        v_u_20:critical_section(function() --[[ Line: 174 ]]
            --[[ Upvalues: (ref 1): v_u_72, (copy 2): p_u_74 ]]
            return v_u_72:test(p_u_74);
        end, function() --[[ Line: 176 ]]
            --[[ Upvalues: (ref 1): v_u_72, (copy 2): p_u_74 ]]
            v_u_72:retain(p_u_74)
        end, function() --[[ Line: 178 ]]
            --[[ Upvalues: (ref 1): v_u_72, (copy 2): p_u_74 ]]
            v_u_72:release(p_u_74)
        end, function() --[[ Line: 180 ]]
            --[[ Upvalues: (ref 1): v_u_72, (copy 2): p_u_74, (ref 3): f_verify_playerblob, (ref 4): v_u_77, (copy 5): p_u_75, (ref 6): v_u_6, (ref 7): p_u_52 ]]
            v_u_72:retain(p_u_74)
            f_verify_playerblob(p_u_74, v_u_77, function(p_u_78, p_u_79) --[[ Line: 182 ]]
                --[[ Upvalues: (ref 1): p_u_75, (ref 2): v_u_6, (ref 3): p_u_52, (ref 4): v_u_72, (ref 5): p_u_74 ]]
                local function v_u_80() --[[ Line: 183 ]]
                    --[[ Upvalues: (ref 1): p_u_75, (copy 2): p_u_78, (copy 3): p_u_79 ]]
                    p_u_75(p_u_78, p_u_79)
                end;
                local v81, v82 = v_u_6:try(function() --[[ Line: 158 ]]
                    --[[ Upvalues: (copy 1): v_u_80 ]]
                    v_u_80()
                end)
                if not v81 then
                    p_u_52._error_report:evt_report_error(v82)
                end;
                v_u_72:release(p_u_74)
            end)
        end)
    end;
    v_u_53.get_ab_verified_cached_blobs = function(_, p_u_83, p_u_84, p_u_85, p_u_86) --[[ Name: get_ab_verified_cached_blobs ]] --[[ Line: 191 ]]
        --[[ Upvalues: (ref 1): v_u_19, (ref 2): v_u_20, (copy 3): v_u_72, (ref 4): v_u_21, (ref 5): v_u_6, (copy 6): p_u_52, (copy 7): f_verify_playerblob ]]
        v_u_19:is_true(p_u_83 ~= p_u_84, "PlayerBlobManagerServer:get_ab_verified_cached_blobs player_id_a == player_id_b")
        v_u_20:critical_section(function() --[[ Line: 194 ]]
            --[[ Upvalues: (ref 1): v_u_72, (copy 2): p_u_83, (copy 3): p_u_84 ]]
            local v87 = v_u_72:test(p_u_83)
            if v87 then
                v87 = v_u_72:test(p_u_84)
            end;
            return v87;
        end, function() --[[ Line: 196 ]]
            --[[ Upvalues: (ref 1): v_u_72, (copy 2): p_u_83, (copy 3): p_u_84 ]]
            v_u_72:retain(p_u_83)
            v_u_72:retain(p_u_84)
        end, function() --[[ Line: 199 ]]
            --[[ Upvalues: (ref 1): v_u_72, (copy 2): p_u_83, (copy 3): p_u_84 ]]
            v_u_72:release(p_u_83)
            v_u_72:release(p_u_84)
        end, function() --[[ Line: 202 ]]
            --[[ Upvalues: (ref 1): v_u_72, (copy 2): p_u_83, (copy 3): p_u_84, (ref 4): v_u_21, (copy 5): p_u_85, (ref 6): v_u_6, (ref 7): p_u_52, (ref 8): f_verify_playerblob, (copy 9): p_u_86 ]]
            v_u_72:retain(p_u_83)
            v_u_72:retain(p_u_84)
            local v_u_88 = nil
            local v_u_89 = nil
            local v_u_90 = nil
            local v_u_91 = nil
            local v_u_95 = v_u_21:new(2, function() --[[ Line: 207 ]]
                --[[ Upvalues: (ref 1): p_u_85, (ref 2): v_u_88, (ref 3): v_u_89, (ref 4): v_u_90, (ref 5): v_u_91, (ref 6): v_u_6, (ref 7): p_u_52, (ref 8): v_u_72, (ref 9): p_u_83, (ref 10): p_u_84 ]]
                local function v_u_92() --[[ Line: 208 ]]
                    --[[ Upvalues: (ref 1): p_u_85, (ref 2): v_u_88, (ref 3): v_u_89, (ref 4): v_u_90, (ref 5): v_u_91 ]]
                    p_u_85(v_u_88, v_u_89, v_u_90, v_u_91)
                end;
                local v93, v94 = v_u_6:try(function() --[[ Line: 158 ]]
                    --[[ Upvalues: (copy 1): v_u_92 ]]
                    v_u_92()
                end)
                if not v93 then
                    p_u_52._error_report:evt_report_error(v94)
                end;
                v_u_72:release(p_u_83)
                v_u_72:release(p_u_84)
            end)
            f_verify_playerblob(p_u_83, p_u_86, function(p96, p97) --[[ Line: 214 ]]
                --[[ Upvalues: (ref 1): v_u_88, (ref 2): v_u_90, (copy 3): v_u_95 ]]
                v_u_88 = p96
                v_u_90 = p97
                v_u_95:finish()
            end)
            f_verify_playerblob(p_u_84, p_u_86, function(p98, p99) --[[ Line: 219 ]]
                --[[ Upvalues: (ref 1): v_u_89, (ref 2): v_u_91, (copy 3): v_u_95 ]]
                v_u_89 = p98
                v_u_91 = p99
                v_u_95:finish()
            end)
        end)
    end;
    v_u_53.verified_enqueue_ab_blob_sync_request = function(p_u_100, p_u_101, p_u_102, p_u_103, p_u_104, p_u_105) --[[ Name: verified_enqueue_ab_blob_sync_request ]] --[[ Line: 228 ]]
        --[[ Upvalues: (ref 1): v_u_19, (ref 2): v_u_5, (copy 3): p_u_52, (ref 4): s_HttpService_0, (ref 5): v_u_1, (ref 6): v_u_33, (copy 7): v_u_59 ]]
        v_u_19:is_true(p_u_101 ~= p_u_103, "PlayerBlobManagerServer:get_ab_verified_cached_blobs player_id_a == player_id_b")
        local v_u_106 = false
        local v_u_107 = false
        local v_u_108 = false
        local function _() --[[ Name: complete_on_all_requests_done ]] --[[ Line: 234 ]]
            --[[ Upvalues: (ref 1): v_u_106, (ref 2): v_u_107, (ref 3): v_u_108, (copy 4): p_u_105 ]]
            if v_u_106 == true and (v_u_107 == true and v_u_108 == true) then
                p_u_105(true)
            end;
        end;
        if v_u_5.PlayerBlobDatastoreWebDoNotWritePlayerBlob ~= true then
            p_u_52._api:api_player_sync_blob_ab(p_u_101, s_HttpService_0:JSONEncode(p_u_102), p_u_103, s_HttpService_0:JSONEncode(p_u_104), function(p109, _, p110) --[[ Line: 241 ]]
                --[[ Upvalues: (copy 1): p_u_102, (copy 2): p_u_104, (ref 3): v_u_1, (copy 4): p_u_100, (copy 5): p_u_101, (ref 6): v_u_33, (ref 7): v_u_106, (ref 8): v_u_107, (ref 9): v_u_108, (copy 10): p_u_105, (copy 11): p_u_103 ]]
                if p109 and p110.Ok == true then
                    p_u_102.LastModifiedTime = p110.LastModifiedTimeA
                    p_u_104.LastModifiedTime = p110.LastModifiedTimeB
                else
                    v_u_1:warnf("api_player_sync_blob_ab FAILED, doing full resync")
                end;
                p_u_100:enqueue_blob_sync_request(p_u_101, v_u_33.Get, function() --[[ Line: 249 ]]
                    --[[ Upvalues: (ref 1): v_u_106, (ref 2): v_u_107, (ref 3): v_u_108, (ref 4): p_u_105 ]]
                    v_u_106 = true
                    if v_u_106 == true and v_u_107 == true then
                        if v_u_108 ~= true then
                            return;
                        end;
                        p_u_105(true)
                    end;
                end, true)
                p_u_100:enqueue_blob_sync_request(p_u_103, v_u_33.Get, function() --[[ Line: 253 ]]
                    --[[ Upvalues: (ref 1): v_u_107, (ref 2): v_u_106, (ref 3): v_u_108, (ref 4): p_u_105 ]]
                    v_u_107 = true
                    if v_u_106 == true and v_u_107 == true then
                        if v_u_108 ~= true then
                            return;
                        end;
                        p_u_105(true)
                    end;
                end, true)
            end)
        end;
        v_u_59:write_playerblob_ab_blob(p_u_101, p_u_102, p_u_103, p_u_104, function() --[[ Line: 260 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_108, (copy 3): p_u_100, (copy 4): p_u_101, (ref 5): v_u_33, (ref 6): v_u_106, (ref 7): v_u_107, (copy 8): p_u_105, (copy 9): p_u_103 ]]
            if v_u_5.PlayerBlobDatastoreWebDoNotWritePlayerBlob == true then
                v_u_108 = true
                p_u_100:enqueue_blob_sync_request(p_u_101, v_u_33.Get, function() --[[ Line: 265 ]]
                    --[[ Upvalues: (ref 1): v_u_106, (ref 2): v_u_107, (ref 3): v_u_108, (ref 4): p_u_105 ]]
                    v_u_106 = true
                    if v_u_106 == true and v_u_107 == true then
                        if v_u_108 ~= true then
                            return;
                        end;
                        p_u_105(true)
                    end;
                end, true)
                p_u_100:enqueue_blob_sync_request(p_u_103, v_u_33.Get, function() --[[ Line: 269 ]]
                    --[[ Upvalues: (ref 1): v_u_107, (ref 2): v_u_106, (ref 3): v_u_108, (ref 4): p_u_105 ]]
                    v_u_107 = true
                    if v_u_106 == true and v_u_107 == true then
                        if v_u_108 ~= true then
                            return;
                        end;
                        p_u_105(true)
                    end;
                end, true)
            else
                v_u_108 = true
                if v_u_106 == true and v_u_107 == true then
                    if v_u_108 ~= true then
                        return;
                    end;
                    p_u_105(true)
                end;
            end;
        end)
    end;
    local v_u_111 = v_u_2:new()
    v_u_53.enqueue_blob_sync_request = function(_, p_u_112, p_u_113, p_u_114, p_u_115, p116) --[[ Name: enqueue_blob_sync_request ]] --[[ Line: 283 ]]
        --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_5, (ref 3): v_u_33, (ref 4): v_u_6, (copy 5): p_u_52, (copy 6): v_u_57, (copy 7): v_u_111, (ref 8): v_u_51, (copy 9): v_u_72, (ref 10): v_u_20 ]]
        if p_u_112 == nil or p_u_113 == nil then
            return v_u_1:errf("enqueue_blob_sync_request null player_id");
        end;
        if v_u_5.DoDebugLoadPlayerRbxId == true then
            p_u_112 = v_u_5.DebugLoadPlayerRbxId
        end;
        local function f_test_for_already_enqueued_request(p117, p118) --[[ Name: test_for_already_enqueued_request ]] --[[ Line: 290 ]]
            --[[ Upvalues: (ref 1): p_u_112, (copy 2): p_u_113, (ref 3): v_u_33, (ref 4): v_u_1, (copy 5): p_u_114, (ref 6): v_u_6, (ref 7): p_u_52 ]]
            local v119 = p118 == nil and "" or p118
            if p117:get_user_id() == p_u_112 then
                local v120 = p117:get_request_type()
                local v121 = p_u_113
                local v122
                if (v120 == v_u_33.Get or v120 == v_u_33.GetInitial) and (v121 == v_u_33.Get or v121 == v_u_33.GetInitial) then
                    v122 = true
                elseif v120 == v_u_33.Write then
                    v122 = v121 == v_u_33.Write
                else
                    v122 = false
                end;
                if v122 then
                    if p117:get_callback_count() >= 10 then
                        v_u_1:warnf("Src[%s] Too many callbacks(%d) for player_id(%d) request_type(%d), dropping request", v119, p117:get_callback_count(), p_u_112, p_u_113)
                        return true;
                    else
                        p117:add_callback(function(p_u_123) --[[ Line: 298 ]]
                            --[[ Upvalues: (ref 1): p_u_114, (ref 2): v_u_6, (ref 3): p_u_52 ]]
                            local function v_u_124() --[[ Line: 299 ]]
                                --[[ Upvalues: (ref 1): p_u_114, (copy 2): p_u_123 ]]
                                p_u_114(p_u_123)
                            end;
                            local v125, v126 = v_u_6:try(function() --[[ Line: 158 ]]
                                --[[ Upvalues: (copy 1): v_u_124 ]]
                                v_u_124()
                            end)
                            if not v125 then
                                p_u_52._error_report:evt_report_error(v126)
                            end;
                        end)
                        return true;
                    end;
                end;
            end;
            return false;
        end;
        for v127 = 1, v_u_57:count() do
            if f_test_for_already_enqueued_request(v_u_57:get(v127), "_queued_requests") == true then
                return;
            end;
        end;
        for v128 = 1, v_u_111:count() do
            if f_test_for_already_enqueued_request(v_u_111:get(v128), "_waiting_for_critical_section_queued_requests") == true then
                return;
            end;
        end;
        local v_u_133 = v_u_51:new(p_u_112):set_request_type(p_u_113):add_callback(function(p_u_129) --[[ Line: 330 ]]
            --[[ Upvalues: (copy 1): p_u_114, (ref 2): v_u_6, (ref 3): p_u_52, (ref 4): v_u_72, (ref 5): p_u_112 ]]
            local function v_u_130() --[[ Line: 331 ]]
                --[[ Upvalues: (ref 1): p_u_114, (copy 2): p_u_129 ]]
                p_u_114(p_u_129)
            end;
            local v131, v132 = v_u_6:try(function() --[[ Line: 158 ]]
                --[[ Upvalues: (copy 1): v_u_130 ]]
                v_u_130()
            end)
            if not v131 then
                p_u_52._error_report:evt_report_error(v132)
            end;
            v_u_72:release(p_u_112)
        end)
        if p116 ~= nil then
            p116(v_u_133)
        end;
        v_u_111:push_back(v_u_133)
        v_u_20:critical_section(function() --[[ Line: 349 ]]
            --[[ Upvalues: (copy 1): p_u_115, (ref 2): v_u_72, (ref 3): p_u_112 ]]
            if p_u_115 == true then
                return false;
            else
                return v_u_72:test(p_u_112);
            end;
        end, function() --[[ Line: 355 ]]
            --[[ Upvalues: (ref 1): v_u_72, (ref 2): p_u_112 ]]
            v_u_72:retain(p_u_112)
        end, function() --[[ Line: 358 ]]
            --[[ Upvalues: (ref 1): v_u_72, (ref 2): p_u_112 ]]
            v_u_72:release(p_u_112)
        end, function() --[[ Line: 361 ]]
            --[[ Upvalues: (ref 1): v_u_72, (ref 2): p_u_112, (ref 3): v_u_111, (copy 4): v_u_133, (ref 5): v_u_57 ]]
            v_u_72:retain(p_u_112)
            v_u_111:remove(v_u_133)
            v_u_57:push_back(v_u_133)
        end)
    end;
    v_u_53.start = function(p_u_134) --[[ Name: start ]] --[[ Line: 377 ]]
        --[[ Upvalues: (copy 1): p_u_52, (ref 2): v_u_4, (copy 3): v_u_58, (ref 4): v_u_1, (copy 5): v_u_55, (ref 6): v_u_33, (ref 7): v_u_5, (ref 8): v_u_8, (ref 9): v_u_6, (ref 10): v_u_11, (ref 11): v_u_12, (ref 12): v_u_16, (ref 13): v_u_13, (ref 14): v_u_7, (ref 15): v_u_17, (ref 16): v_u_18, (ref 17): v_u_24, (ref 18): v_u_25 ]]
        local function f_get_time_info_table() --[[ Name: get_time_info_table ]] --[[ Line: 378 ]]
            --[[ Upvalues: (ref 1): p_u_52 ]]
            return {
                ["GlobalTime"] = p_u_52._api:get_global_time(),
                ["DayID"] = p_u_52._api:get_day_id(),
                ["WeekID"] = p_u_52._api:get_week_id(),
                ["MonthID"] = p_u_52._api:get_month_id(),
                ["TimeToNextDaySec"] = p_u_52._api:get_time_to_next_day_sec(),
                ["TimeToNextWeekSec"] = p_u_52._api:get_time_to_next_week_sec(),
                ["TimeToNextMonthSec"] = p_u_52._api:get_time_to_next_month_sec(),
                ["ServerID"] = p_u_52._api:get_spid()
            };
        end;
        local function _(p135) --[[ Name: get_player_info_table ]] --[[ Line: 391 ]]
            --[[ Upvalues: (ref 1): p_u_52 ]]
            local v136, v137 = p_u_52._guild_manager:is_player_in_guild(p135)
            return {
                ["IsInGuild"] = v136,
                ["GuildID"] = v137
            };
        end;
        local function f_get_server_info_table(p_u_138) --[[ Name: get_server_info_table ]] --[[ Line: 399 ]]
            --[[ Upvalues: (ref 1): p_u_52 ]]
            local v_u_139 = nil
            local v_u_140 = nil
            local v_u_141 = nil
            local function _() --[[ Name: callback_if_all_loaded ]] --[[ Line: 401 ]]
                --[[ Upvalues: (ref 1): v_u_139, (ref 2): v_u_140, (ref 3): v_u_141, (ref 4): p_u_138 ]]
                if v_u_139 ~= nil and (v_u_140 ~= nil and (v_u_141 ~= nil and p_u_138 ~= nil)) then
                    p_u_138({
                        ["MissionData"] = v_u_139,
                        ["LeaderboardInfo"] = v_u_140,
                        ["SongShopData"] = v_u_141
                    })
                    p_u_138 = nil
                end;
            end;
            p_u_52._mission_manager:get_mission_data(function(p142) --[[ Line: 413 ]]
                --[[ Upvalues: (ref 1): v_u_139, (ref 2): v_u_140, (ref 3): v_u_141, (ref 4): p_u_138 ]]
                v_u_139 = p142
                if v_u_139 ~= nil and (v_u_140 ~= nil and (v_u_141 ~= nil and p_u_138 ~= nil)) then
                    p_u_138({
                        ["MissionData"] = v_u_139,
                        ["LeaderboardInfo"] = v_u_140,
                        ["SongShopData"] = v_u_141
                    })
                    p_u_138 = nil
                end;
            end)
            p_u_52._leaderboard_manager:get_validated_leaderboard_info(function(p143) --[[ Line: 417 ]]
                --[[ Upvalues: (ref 1): v_u_140, (ref 2): v_u_139, (ref 3): v_u_141, (ref 4): p_u_138 ]]
                v_u_140 = p143
                if v_u_139 ~= nil and (v_u_140 ~= nil and (v_u_141 ~= nil and p_u_138 ~= nil)) then
                    p_u_138({
                        ["MissionData"] = v_u_139,
                        ["LeaderboardInfo"] = v_u_140,
                        ["SongShopData"] = v_u_141
                    })
                    p_u_138 = nil
                end;
            end)
            p_u_52._shop_manager:get_updated_shop_info(function(p144) --[[ Line: 421 ]]
                --[[ Upvalues: (ref 1): v_u_141, (ref 2): v_u_139, (ref 3): v_u_140, (ref 4): p_u_138 ]]
                v_u_141 = p144
                if v_u_139 ~= nil and (v_u_140 ~= nil and (v_u_141 ~= nil and p_u_138 ~= nil)) then
                    p_u_138({
                        ["MissionData"] = v_u_139,
                        ["LeaderboardInfo"] = v_u_140,
                        ["SongShopData"] = v_u_141
                    })
                    p_u_138 = nil
                end;
            end)
        end;
        p_u_52._evt:wait_on_event(v_u_4.EVT_PlayerBlob_ClientInitialRequestSync, function(p_u_145) --[[ Line: 427 ]]
            --[[ Upvalues: (ref 1): v_u_58, (ref 2): v_u_1, (ref 3): v_u_55, (ref 4): p_u_52, (copy 5): p_u_134, (ref 6): v_u_33, (copy 7): f_get_server_info_table, (ref 8): v_u_5, (ref 9): v_u_8, (ref 10): v_u_4, (copy 11): f_get_time_info_table ]]
            if v_u_58:is_on_cooldown(p_u_145.UserId) == true then
                return v_u_1:warnf("EVT_PlayerBlob_ClientInitialRequestSync from [%s](%d) on cooldown", p_u_145.Name, p_u_145.UserId);
            end;
            v_u_58:add_cooldown_to_id(p_u_145.UserId, 30)
            v_u_1:puts("EVT_PlayerBlob_ClientInitialRequestSync from [%s](%d)", p_u_145.Name, p_u_145.UserId)
            v_u_55:remove(p_u_145.UserId)
            p_u_52._player_model_cache:load_character_for_player(p_u_145, function() --[[ Line: 435 ]]
                --[[ Upvalues: (ref 1): v_u_1, (copy 2): p_u_145, (ref 3): p_u_134, (ref 4): v_u_33, (ref 5): f_get_server_info_table, (ref 6): v_u_5, (ref 7): p_u_52, (ref 8): v_u_8, (ref 9): v_u_4, (ref 10): f_get_time_info_table ]]
                v_u_1:puts("EVT_PlayerBlob_ClientInitialRequestSync enqueue_blob_sync_request(GET) from [%s](%d)", p_u_145.Name, p_u_145.UserId)
                p_u_134:enqueue_blob_sync_request(p_u_145.UserId, v_u_33.GetInitial, function(p_u_146) --[[ Line: 437 ]]
                    --[[ Upvalues: (ref 1): f_get_server_info_table, (ref 2): v_u_1, (ref 3): p_u_145, (ref 4): v_u_5, (ref 5): p_u_52, (ref 6): v_u_8, (ref 7): v_u_4, (ref 8): f_get_time_info_table ]]
                    f_get_server_info_table(function(p147) --[[ Line: 438 ]]
                        --[[ Upvalues: (ref 1): v_u_1, (ref 2): p_u_145, (ref 3): v_u_5, (ref 4): p_u_52, (ref 5): v_u_8, (copy 6): p_u_146, (ref 7): v_u_4, (ref 8): f_get_time_info_table ]]
                        v_u_1:puts("EVT_PlayerBlob_ClientInitialRequestSync success from [%s](%d)", p_u_145.Name, p_u_145.UserId)
                        if v_u_5.PlayerBlobWebOnlyReadOnInitialRequest ~= true then
                            p_u_52._api:api_player_login_evt(p_u_145.UserId, p_u_145.Name)
                        end;
                        local v148 = v_u_8:to_json(p_u_146)
                        local l__evt_0 = p_u_52._evt
                        local l_EVT_PlayerBlob_ServerBlobSync_0 = v_u_4.EVT_PlayerBlob_ServerBlobSync
                        local v149 = p_u_145
                        local v150, v151 = p_u_52._guild_manager:is_player_in_guild(p_u_145.UserId)
                        l__evt_0:fire_event_to_client(l_EVT_PlayerBlob_ServerBlobSync_0, v149, v148, {
                            ["IsInGuild"] = v150,
                            ["GuildID"] = v151
                        }, p_u_52._api:get_day_event_list():to_table(), f_get_time_info_table(), p147)
                    end)
                end)
            end, true)
        end)
        p_u_52._evt:wait_on_event(v_u_4.EVT_PlayerBlob_ClientRequestSync, function(p_u_152) --[[ Line: 459 ]]
            --[[ Upvalues: (ref 1): v_u_6, (copy 2): f_get_server_info_table, (ref 3): v_u_5, (ref 4): v_u_1, (ref 5): p_u_52, (copy 6): p_u_134, (ref 7): v_u_33, (ref 8): v_u_8, (ref 9): v_u_4, (copy 10): f_get_time_info_table ]]
            local v_u_153 = v_u_6:get_player_id(p_u_152)
            f_get_server_info_table(function(p_u_154) --[[ Line: 461 ]]
                --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_6, (ref 3): v_u_1, (ref 4): p_u_52, (copy 5): v_u_153, (ref 6): p_u_134, (copy 7): p_u_152, (ref 8): v_u_33, (ref 9): v_u_8, (ref 10): v_u_4, (ref 11): f_get_time_info_table ]]
                if v_u_5.DebugErrSyncTest == true then
                    if v_u_6:rand_rangei(0, 100) < 10 then
                        v_u_1:errf("DebugErrSyncTest")
                    else
                        local v155 = v_u_6:rand_rangei(0, 20)
                        v_u_1:warnf("DebugErrSyncTest(%d)", v155)
                        wait(v155)
                    end;
                end;
                local v_u_156 = p_u_52._player_blob_manager:get_cached_blob(v_u_153)
                local v157 = p_u_52._api:get_day_id()
                if v_u_156 == nil then
                    p_u_134:enqueue_blob_sync_request(p_u_152.UserId, v_u_33.Get, function(p158) --[[ Line: 477 ]]
                        --[[ Upvalues: (ref 1): v_u_156, (ref 2): v_u_1, (ref 3): p_u_152, (ref 4): v_u_8, (ref 5): p_u_52, (ref 6): v_u_4, (ref 7): f_get_time_info_table, (copy 8): p_u_154 ]]
                        v_u_156 = p158
                        v_u_1:warnf("EVT_PlayerBlob_ClientRequestSync[%s](%d) unexpected Request(Get) response", p_u_152.Name, p_u_152.UserId)
                        local v159 = v_u_8:to_json(v_u_156)
                        local l__evt_1 = p_u_52._evt
                        local l_EVT_PlayerBlob_ServerBlobSync_1 = v_u_4.EVT_PlayerBlob_ServerBlobSync
                        local v160 = p_u_152
                        local v161, v162 = p_u_52._guild_manager:is_player_in_guild(p_u_152.UserId)
                        l__evt_1:fire_event_to_client(l_EVT_PlayerBlob_ServerBlobSync_1, v160, v159, {
                            ["IsInGuild"] = v161,
                            ["GuildID"] = v162
                        }, p_u_52._api:get_day_event_list():to_table(), f_get_time_info_table(), p_u_154)
                    end)
                    return v_u_1:warnf("EVT_PlayerBlob_ClientRequestSync[%s](%d) does not contain cached blob stack(%s), sending unexpected Request(Get)", p_u_152.Name, p_u_152.UserId, debug.traceback());
                end;
                if v_u_156.LastUpdatedDay == v157 then
                    local v163 = v_u_8:to_json(v_u_156)
                    local l__evt_2 = p_u_52._evt
                    local l_EVT_PlayerBlob_ServerBlobSync_2 = v_u_4.EVT_PlayerBlob_ServerBlobSync
                    local v164 = p_u_152
                    local v165, v166 = p_u_52._guild_manager:is_player_in_guild(p_u_152.UserId)
                    l__evt_2:fire_event_to_client(l_EVT_PlayerBlob_ServerBlobSync_2, v164, v163, {
                        ["IsInGuild"] = v165,
                        ["GuildID"] = v166
                    }, p_u_52._api:get_day_event_list():to_table(), f_get_time_info_table(), p_u_154)
                else
                    p_u_52._player_blob_manager:get_verified_cached_blob(v_u_153, function(p167) --[[ Line: 496 ]]
                        --[[ Upvalues: (ref 1): v_u_8, (ref 2): p_u_52, (ref 3): v_u_4, (ref 4): p_u_152, (ref 5): f_get_time_info_table, (copy 6): p_u_154 ]]
                        local v168 = v_u_8:to_json(p167)
                        local l__evt_3 = p_u_52._evt
                        local l_EVT_PlayerBlob_ServerBlobSync_3 = v_u_4.EVT_PlayerBlob_ServerBlobSync
                        local v169 = p_u_152
                        local v170, v171 = p_u_52._guild_manager:is_player_in_guild(p_u_152.UserId)
                        l__evt_3:fire_event_to_client(l_EVT_PlayerBlob_ServerBlobSync_3, v169, v168, {
                            ["IsInGuild"] = v170,
                            ["GuildID"] = v171
                        }, p_u_52._api:get_day_event_list():to_table(), f_get_time_info_table(), p_u_154)
                    end)
                end;
            end)
        end)
        p_u_52._evt:wait_on_event(v_u_4.EVT_PlayerSettings_ClientUpdate, function(p_u_172, p_u_173) --[[ Line: 523 ]]
            --[[ Upvalues: (ref 1): p_u_52, (ref 2): v_u_4, (ref 3): v_u_11, (ref 4): v_u_8 ]]
            local function f_response(p174) --[[ Name: response ]] --[[ Line: 524 ]]
                --[[ Upvalues: (ref 1): p_u_52, (ref 2): v_u_4, (copy 3): p_u_172 ]]
                p_u_52._evt:fire_event_to_client(v_u_4.EVT_PlayerSettings_ServerAcknowledgeUpdate, p_u_172, p174)
            end;
            p_u_52._player_blob_manager:get_verified_cached_blob(p_u_172.UserId, function(p175) --[[ Line: 528 ]]
                --[[ Upvalues: (copy 1): f_response, (ref 2): v_u_11, (ref 3): v_u_8, (copy 4): p_u_173, (ref 5): p_u_52, (copy 6): p_u_172 ]]
                if p175 == nil then
                    return f_response(false);
                end;
                local v176 = v_u_11:new()
                v176:load_from_json_str(v_u_8:get_player_settings_str(p175))
                local v177 = v_u_11:new()
                v177:load_from_json_str(p_u_173)
                if v_u_11:server_validate_client_updated_player_settings(v176, v177) ~= true then
                    return f_response(false);
                end;
                v_u_8:set_player_settings_str(p175, v177:to_json())
                p_u_52._player_blob_manager:enqueue_blob_sync_request(p_u_172.UserId, v_u_8.PlayerBlobRequestType.Write, function(_) --[[ Line: 548 ]]
                    --[[ Upvalues: (ref 1): f_response ]]
                    return f_response(true);
                end)
            end)
        end)
        p_u_52._evt:wait_on_event(v_u_4.EVT_PlayerBlob_ClientSetTitle, function(p_u_178, p_u_179) --[[ Line: 555 ]]
            --[[ Upvalues: (ref 1): p_u_52, (ref 2): v_u_4, (ref 3): v_u_12, (ref 4): v_u_16, (ref 5): v_u_8 ]]
            local function f_response(p180) --[[ Name: response ]] --[[ Line: 556 ]]
                --[[ Upvalues: (ref 1): p_u_52, (ref 2): v_u_4, (copy 3): p_u_178 ]]
                p_u_52._evt:fire_event_to_client(v_u_4.EVT_PlayerBlob_ServerSetTitleResponse, p_u_178, p180)
            end;
            p_u_52._player_blob_manager:get_verified_cached_blob(p_u_178.UserId, function(p181) --[[ Line: 559 ]]
                --[[ Upvalues: (ref 1): v_u_12, (copy 2): p_u_179, (ref 3): p_u_52, (copy 4): f_response, (ref 5): v_u_16, (copy 6): p_u_178, (ref 7): v_u_8, (ref 8): v_u_4 ]]
                if v_u_12:is_titleid_vip_only(p_u_179) then
                    if v_u_12:playerblob_has_vip_for_current_day(p181, p_u_52._api:get_day_id()) ~= true then
                        return f_response(false);
                    end;
                elseif p_u_179 == v_u_16:singleton():get_guild_title_id() then
                    if p_u_52._guild_manager:is_player_in_guild(p_u_178.UserId) ~= true then
                        return f_response(false);
                    end;
                elseif v_u_8:owns_title_id(p181, p_u_179) ~= true then
                    return f_response(false);
                end;
                v_u_8:set_title_id(p181, p_u_179)
                p_u_52._player_blob_manager:enqueue_blob_sync_request(p_u_178.UserId, v_u_8.PlayerBlobRequestType.Write, function(_) --[[ Line: 577 ]]
                    --[[ Upvalues: (ref 1): p_u_52, (ref 2): v_u_4, (ref 3): p_u_178 ]]
                    p_u_52._evt:fire_event_to_client(v_u_4.EVT_PlayerBlob_ServerSetTitleResponse, p_u_178, true)
                    p_u_52._lobby_manager:push_player_info_updated(p_u_178.UserId)
                end)
            end)
        end)
        p_u_52._evt:wait_on_event(v_u_4.EVT_PlayerBlob_ClientSetEquippedDances, function(p_u_182, p_u_183) --[[ Line: 585 ]]
            --[[ Upvalues: (ref 1): p_u_52, (ref 2): v_u_4, (ref 3): v_u_13, (ref 4): v_u_8 ]]
            local function _(p184) --[[ Name: response ]] --[[ Line: 586 ]]
                --[[ Upvalues: (ref 1): p_u_52, (ref 2): v_u_4, (copy 3): p_u_182 ]]
                p_u_52._evt:fire_event_to_client(v_u_4.EVT_PlayerBlob_ServerSetEquippedDancesResponse, p_u_182, p184)
            end;
            p_u_52._player_blob_manager:get_verified_cached_blob(p_u_182.UserId, function(p185) --[[ Line: 589 ]]
                --[[ Upvalues: (ref 1): v_u_13, (copy 2): p_u_183, (ref 3): p_u_52, (copy 4): p_u_182, (ref 5): v_u_8, (ref 6): v_u_4 ]]
                v_u_13:validate_playerblob_danceequipped_danceowned(p_u_183, p185.DanceOwned)
                v_u_13:write_dance_equipped(p185, p_u_183)
                v_u_13:validate_playerblob(p185)
                p_u_52._player_blob_manager:enqueue_blob_sync_request(p_u_182.UserId, v_u_8.PlayerBlobRequestType.Write, function(_) --[[ Line: 596 ]]
                    --[[ Upvalues: (ref 1): p_u_52, (ref 2): v_u_4, (ref 3): p_u_182 ]]
                    p_u_52._evt:fire_event_to_client(v_u_4.EVT_PlayerBlob_ServerSetEquippedDancesResponse, p_u_182, true)
                end)
            end)
        end)
        p_u_52._evt:wait_on_event(v_u_4.EVT_RobloxPremium_ClientClaim, function(p_u_186) --[[ Line: 603 ]]
            --[[ Upvalues: (ref 1): p_u_52, (ref 2): v_u_4, (ref 3): v_u_5, (ref 4): v_u_7, (ref 5): v_u_1, (ref 6): v_u_17, (ref 7): v_u_8 ]]
            local function f_response(p187) --[[ Name: response ]] --[[ Line: 604 ]]
                --[[ Upvalues: (ref 1): p_u_52, (ref 2): v_u_4, (copy 3): p_u_186 ]]
                p_u_52._evt:fire_event_to_client(v_u_4.EVT_RobloxPremium_ServerClaimResponse, p_u_186, p187)
            end;
            if v_u_5.PremiumRewardsEnabled ~= true then
                p_u_52._api:api_report_evt(v_u_7.ReportEvt_ErrPremiumNotEnabled, p_u_186.UserId, 0, "")
                return v_u_1:errf("premium_rewards_fail");
            end;
            if v_u_17:player_is_roblox_premium(p_u_186) ~= true then
                return f_response(false);
            end;
            local v188 = p_u_52._player_blob_manager:get_cached_blob(p_u_186.UserId)
            if v_u_17:playerblob_has_claimed_premium_rewards(v188) == true then
                return f_response(false);
            end;
            v_u_17:apply_rewards_to_playerblob_dayid(v188, p_u_52._api:get_day_id())
            p_u_52._api:api_report_evt(v_u_7.ReportEvt_ClaimPremiumRewards, p_u_186.UserId, 0, "")
            p_u_52._player_blob_manager:enqueue_blob_sync_request(p_u_186.UserId, v_u_8.PlayerBlobRequestType.Write, function(_) --[[ Line: 625 ]]
                --[[ Upvalues: (ref 1): p_u_52, (ref 2): v_u_4, (copy 3): p_u_186 ]]
                p_u_52._evt:fire_event_to_client(v_u_4.EVT_RobloxPremium_ServerClaimResponse, p_u_186, true)
                p_u_52._lobby_manager:push_player_info_updated(p_u_186.UserId)
            end)
        end)
        p_u_52._evt:wait_on_event(v_u_4.EVT_RobloxGroup_ClientClaim, function(p_u_189) --[[ Line: 632 ]]
            --[[ Upvalues: (ref 1): p_u_52, (ref 2): v_u_4, (ref 3): v_u_5, (ref 4): v_u_1, (ref 5): v_u_18, (ref 6): v_u_24 ]]
            local function f_response(p190, p191) --[[ Name: response ]] --[[ Line: 633 ]]
                --[[ Upvalues: (ref 1): p_u_52, (ref 2): v_u_4, (copy 3): p_u_189 ]]
                p_u_52._evt:fire_event_to_client(v_u_4.EVT_RobloxGroup_ServerClaimResponse, p_u_189, p190, p191)
            end;
            if v_u_5.GroupRewardsEnabled ~= true then
                return v_u_1:errf("EVT_RobloxGroup_ServerClaimResponse not enabled");
            end;
            local v_u_192 = p_u_52._player_blob_manager:get_cached_blob(p_u_189.UserId)
            if v_u_18:playerblob_has_claimed_group_rewards(v_u_192) == true then
                return f_response(false, "Already claimed reward.");
            end;
            spawn(function() --[[ Line: 639 ]]
                --[[ Upvalues: (copy 1): p_u_189, (ref 2): p_u_52, (copy 3): f_response, (ref 4): v_u_18, (copy 5): v_u_192, (ref 6): v_u_24, (ref 7): v_u_4 ]]
                local v_u_193 = p_u_189:IsInGroup(3155023)
                p_u_52._post_fn:enqueue_function(function() --[[ Line: 642 ]]
                    --[[ Upvalues: (copy 1): v_u_193, (ref 2): f_response, (ref 3): v_u_18, (ref 4): p_u_52, (ref 5): v_u_192, (ref 6): v_u_24, (ref 7): p_u_189, (ref 8): v_u_4 ]]
                    if v_u_193 ~= true then
                        return f_response(false, "You have not joined the RobeatsDev group!\nJoin the group from the game page (click \"By RobeatsDev\") and try again.");
                    end;
                    v_u_24:server_sync_reward_params(p_u_52, p_u_189, v_u_18:apply_rewards_to_playerblob(p_u_52, v_u_192), function(p194) --[[ Line: 648 ]]
                        --[[ Upvalues: (ref 1): p_u_52, (ref 2): v_u_4, (ref 3): p_u_189 ]]
                        p_u_52._evt:fire_event_to_client(v_u_4.EVT_RobloxGroup_ServerClaimResponse, p_u_189, true, p194)
                    end)
                end)
            end)
        end)
        p_u_52._evt:wait_on_event(v_u_4.EVT_PlayerBlob_ClaimLoginRewardClient, function(p_u_195) --[[ Line: 655 ]]
            --[[ Upvalues: (ref 1): p_u_52, (ref 2): v_u_4, (ref 3): v_u_25, (ref 4): v_u_24 ]]
            local function f_response(p196, p197, p198, p199) --[[ Name: response ]] --[[ Line: 656 ]]
                --[[ Upvalues: (ref 1): p_u_52, (ref 2): v_u_4, (copy 3): p_u_195 ]]
                p_u_52._evt:fire_event_to_client(v_u_4.EVT_PlayerBlob_ClaimLoginRewardServer, p_u_195, p196, p197, p198 == nil and {} or p198, p199 == nil and 0 or p199)
            end;
            local v_u_200 = p_u_52._api:get_day_id()
            local v_u_201 = p_u_52._api:get_month_id()
            p_u_52._player_blob_manager:get_verified_cached_blob(p_u_195.UserId, function(p202) --[[ Line: 665 ]]
                --[[ Upvalues: (copy 1): f_response, (ref 2): v_u_25, (copy 3): v_u_200, (copy 4): v_u_201, (ref 5): v_u_24, (ref 6): p_u_52, (copy 7): p_u_195, (ref 8): v_u_4 ]]
                if p202 == nil then
                    return f_response(false, "no playerblob");
                end;
                if v_u_25:playerblob_can_claim_login_reward_for_dayid_monthid(p202, v_u_200, v_u_201) ~= true then
                    return f_response(false, "Already claimed for today.");
                end;
                local v_u_203 = v_u_25:get_reward_day_count_for_playerblob_dayid_monthid(p202, v_u_200, v_u_201)
                local v204 = v_u_25:get_reward_for_day_count(v_u_203, v_u_201)
                v_u_25:playerblob_mark_as_claimed_for_dayid_monthid(p202, v_u_200, v_u_201)
                if v204:count() == 0 then
                    return f_response(false, "No rewards for today.");
                end;
                local v_u_205 = v_u_24:claim_reward_info_list_to_playerblob(p_u_52, p202, v204)
                v_u_24:server_sync_reward_params(p_u_52, p_u_195, v_u_205, function(p206) --[[ Line: 677 ]]
                    --[[ Upvalues: (ref 1): v_u_24, (copy 2): v_u_205, (copy 3): v_u_203, (ref 4): p_u_52, (ref 5): v_u_4, (ref 6): p_u_195 ]]
                    local v207 = v_u_24.RewardInfo:list_to_table(v_u_24:reward_params_get_resolved_reward_list(v_u_205))
                    local v208 = v_u_203
                    p_u_52._evt:fire_event_to_client(v_u_4.EVT_PlayerBlob_ClaimLoginRewardServer, p_u_195, true, p206, v207 == nil and {} or v207, v208 == nil and 0 or v208)
                end)
            end)
        end)
    end;
    v_u_53.player_disconnecting = function(_, p209) --[[ Name: player_disconnecting ]] --[[ Line: 685 ]]
        --[[ Upvalues: (copy 1): v_u_54, (copy 2): v_u_55, (copy 3): v_u_58 ]]
        if v_u_54:contains(p209) then
            v_u_55:add(p209, true)
        end;
        v_u_58:remove_cooldown_from_id(p209)
    end;
    v_u_53.player_blob_verify_action = function(_, p_u_210, p_u_211) --[[ Name: player_blob_verify_action ]] --[[ Line: 692 ]]
        --[[ Upvalues: (ref 1): v_u_8, (copy 2): p_u_52, (ref 3): v_u_1, (ref 4): v_u_5, (ref 5): v_u_28, (ref 6): v_u_31, (ref 7): v_u_30, (ref 8): v_u_12, (ref 9): v_u_16, (ref 10): v_u_6, (ref 11): v_u_29 ]]
        local v212 = false
        if v_u_8:is_banned(p_u_210) == true then
            return p_u_211(p_u_210);
        end;
        local v213 = p_u_52._api:get_day_id()
        if p_u_210.LastUpdatedDay ~= v213 then
            v_u_1:puts("PlayerBlobManagerServer:player_blob_verify_action() userid(%s) player_blob.LastUpdatedDay(%s) ~= current_day_id(%s), wiping DailySection", tostring(p_u_210.UserId), tostring(p_u_210.LastUpdatedDay), (tostring(v213)))
            v212 = true
            p_u_210.LastUpdatedDay = v213
            if v_u_5.PlayerBlobDatastoreDoReadComponentsFromDatastore == true then
                v_u_28.DailySection:clear_playerblob(p_u_210)
            end;
        end;
        if v_u_5.PlayerBlobDatastoreDoReadComponentsFromDatastore == true then
            local v214 = p_u_52._api:get_week_id()
            local v215 = false
            for _, v216 in v_u_28.WeeklySection:create_from_playerblob(p_u_210):get_week_mission_progress():key_itr() do
                if v216:get_week_id() ~= v214 then
                    v215 = true
                    break;
                end;
            end;
            if v215 == true then
                v_u_28.WeeklySection:clear_playerblob(p_u_210)
                v_u_1:puts("PlayerBlobManagerServer:player_blob_verify_action() userid(%s) has_any_mismatched_week, wiping WeeklySection", (tostring(p_u_210.UserId)))
                v212 = true
            end;
        end;
        local v217 = p_u_52._api:get_month_id()
        local v_u_218
        if v_u_5.UseChallengePassV2 == true then
            v_u_218 = v_u_31:validate_playerblob_to_current_day_week_month_id(p_u_210, p_u_52._api:get_day_id(), p_u_52._api:get_week_id(), v217) and true or v212
        else
            v_u_218 = v_u_30:validate_playerblob_to_current_month_id(p_u_210, v217) and true or v212
        end;
        if v_u_12:playerblob_has_vip_for_current_day(p_u_210, v213) ~= true then
            if v_u_16:singleton():get_title_for_id(p_u_210.CurrentTitleID):is_vip_only() == true then
                p_u_210.CurrentTitleID = v_u_16:singleton():get_default_title():get_title_id()
                v_u_218 = true
            end;
            v_u_6:ptry(function() --[[ Line: 752 ]]
                --[[ Upvalues: (copy 1): p_u_210, (ref 2): v_u_29, (ref 3): v_u_218 ]]
                if v_u_29:singleton():get_fevericon_for_id(p_u_210.FeverIcon):is_vip_only() == true then
                    v_u_218 = true
                    p_u_210.FeverIcon = v_u_29:singleton():get_default_fevericon():get_id()
                end;
            end)
        end;
        if p_u_210.CurrentTitleID == v_u_16:singleton():get_guild_title_id() and p_u_52._guild_manager:is_player_in_guild(p_u_210.UserId) ~= true then
            p_u_210.CurrentTitleID = v_u_16:singleton():get_default_title():get_title_id()
            v_u_218 = true
        end;
        if v_u_218 == true then
            p_u_52._player_blob_manager:enqueue_blob_sync_request(p_u_210.UserId, v_u_8.PlayerBlobRequestType.Write, function(p219) --[[ Line: 780 ]]
                --[[ Upvalues: (copy 1): p_u_211 ]]
                if p_u_211 then
                    p_u_211(p219)
                end;
            end, true)
        else
            p_u_211(p_u_210)
        end;
    end;
    local function f_perform_queued_request_get(p_u_220) --[[ Name: perform_queued_request_get ]] --[[ Line: 792 ]]
        --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_33, (ref 3): v_u_1, (ref 4): v_u_8, (copy 5): v_u_59, (copy 6): p_u_52, (ref 7): v_u_7, (ref 8): v_u_6, (copy 9): v_u_54, (ref 10): v_u_28, (ref 11): v_u_11, (copy 12): v_u_53, (ref 13): v_u_13, (ref 14): v_u_9, (ref 15): v_u_10, (ref 16): v_u_23 ]]
        local v_u_221 = nil
        local v_u_222 = nil
        local v_u_223 = nil
        local v_u_224 = nil
        local v_u_225 = nil
        local v_u_226 = false
        local function f_callback_if_all_loaded() --[[ Name: callback_if_all_loaded ]] --[[ Line: 798 ]]
            --[[ Upvalues: (ref 1): v_u_221, (ref 2): v_u_222, (ref 3): v_u_223, (ref 4): v_u_224, (ref 5): v_u_5, (ref 6): v_u_225, (ref 7): v_u_226, (copy 8): p_u_220, (ref 9): v_u_33, (ref 10): v_u_1, (ref 11): v_u_8, (ref 12): v_u_59, (ref 13): p_u_52, (ref 14): v_u_7, (ref 15): v_u_6, (ref 16): v_u_54, (ref 17): v_u_28, (ref 18): v_u_11, (ref 19): v_u_53, (ref 20): v_u_13, (ref 21): v_u_9, (ref 22): v_u_10, (ref 23): v_u_23 ]]
            if v_u_221 == nil or (v_u_222 == nil or (v_u_223 == nil or v_u_224 == nil)) then
                return;
            elseif v_u_5.PlayerBlobDatastoreDoReadBlobFromDatastore ~= true or v_u_225 ~= nil then
                local v227
                if v_u_5.PlayerBlobOnlyReadFromDatastore == true then
                    if v_u_226 == true then
                        v227 = v_u_225
                    else
                        if p_u_220:get_request_type() == v_u_33.GetInitial then
                            v_u_1:puts("PlayerBlobManagerServer perform_queued_request_get() GetInitial datastore did not have playerblob, creating new playerblob(%d)", p_u_220:get_user_id())
                        end;
                        v227 = v_u_8:new()
                        v227.UserId = p_u_220:get_user_id()
                    end;
                elseif v_u_5.PlayerBlobDatastoreDoReadBlobFromDatastore == true then
                    if v_u_226 == true then
                        v227 = v_u_225
                        v227.LastModifiedTime = v_u_221.LastModifiedTime
                    else
                        if p_u_220:get_request_type() == v_u_33.GetInitial then
                            v_u_1:puts("PlayerBlobManagerServer perform_queued_request_get() GetInitial datastore did not have playerblob, using webapi playerblob player(%d)", p_u_220:get_user_id())
                        else
                            v_u_1:warnf("PlayerBlobManagerServer perform_queued_request_get() Get datastore did not have playerblob, using webapi playerblob player(%d)", p_u_220:get_user_id())
                        end;
                        v227 = v_u_221
                        v_u_59:notify_playerid_using_web_playerblob(p_u_220:get_user_id(), v_u_221)
                    end;
                else
                    v227 = v_u_221
                end;
                local v_u_228 = v_u_222
                local v229 = p_u_52._api:get_day_id()
                if v_u_228.DayID ~= nil then
                    pcall(function() --[[ Line: 846 ]]
                        --[[ Upvalues: (ref 1): p_u_52, (copy 2): v_u_228, (ref 3): v_u_7, (ref 4): p_u_220, (ref 5): v_u_6 ]]
                        if p_u_52._api:get_day_id() ~= v_u_228.DayID then
                            p_u_52._api:api_report_evt(v_u_7.ReportEvt_PlayerblobGetDayMismatch, p_u_220:get_user_id(), 0, v_u_6:table_to_string({
                                ["ServerDayID"] = p_u_52._api:get_day_id(),
                                ["ResponseExtraDayID"] = v_u_228.DayID,
                                ["SPID"] = p_u_52._api:get_spid(),
                                ["GlobalTime"] = p_u_52._api:get_global_time()
                            }))
                        end;
                    end)
                    v229 = v_u_228.DayID
                end;
                local v230 = p_u_52._api:get_week_id()
                if v_u_228.WeekID ~= nil then
                    v230 = v_u_228.WeekID
                end;
                local v_u_231
                if v_u_54:contains(p_u_220:get_user_id()) == false then
                    v_u_231 = v_u_8:new()
                    v_u_231.UserId = p_u_220:get_user_id()
                    v_u_8:update_from_obj(v_u_231, v227)
                    v_u_54:add(p_u_220:get_user_id(), v_u_231)
                else
                    v_u_231 = v_u_54:get(p_u_220:get_user_id())
                    v_u_8:update_from_obj(v_u_231, v227)
                end;
                if v_u_5.PlayerBlobDatastoreDoReadComponentsFromDatastore == true then
                    v_u_28.DailySection:write_section_to_playerblob(v_u_223, v_u_231)
                    v_u_28.WeeklySection:write_section_to_playerblob(v_u_224, v_u_231)
                end;
                local v232, v_u_233 = v_u_8:validate_with_dayid_weekid(v_u_231, v229, v230)
                if v232 == true then
                    pcall(function() --[[ Line: 895 ]]
                        --[[ Upvalues: (ref 1): p_u_52, (ref 2): v_u_7, (ref 3): p_u_220, (ref 4): v_u_6, (copy 5): v_u_233, (ref 6): v_u_1 ]]
                        p_u_52._api:api_report_evt(v_u_7.ReportEvt_PlayerblobValidateError, p_u_220:get_user_id(), 0, v_u_6:table_to_string({
                            ["ServerDayID"] = p_u_52._api:get_day_id(),
                            ["SPID"] = p_u_52._api:get_spid(),
                            ["GlobalTime"] = p_u_52._api:get_global_time(),
                            ["Data"] = v_u_233:get_table()
                        }))
                        v_u_1:warnf("Request(Get) PlayerBlob:validate_with_dayid_weekid fail(%s)", v_u_6:table_to_string(v_u_233:get_table()))
                    end)
                end;
                if v_u_231.TutorialStage == v_u_8.TutorialStage.NewPlayer then
                    local v234 = v_u_11:new()
                    v_u_11:apply_new_player_settings(v234)
                    v_u_8:set_player_settings_str(v_u_231, v234:to_json())
                end;
                if v_u_231.UserId ~= p_u_220:get_user_id() then
                    pcall(function() --[[ Line: 919 ]]
                        --[[ Upvalues: (ref 1): p_u_52, (ref 2): v_u_7, (ref 3): p_u_220, (ref 4): v_u_231, (ref 5): v_u_6, (ref 6): v_u_1 ]]
                        p_u_52._api:api_report_evt(v_u_7.ReportEvt_PlayerblobUserIdMismatch, p_u_220:get_user_id(), v_u_231.UserId, v_u_6:table_to_string(v_u_231))
                        v_u_1:warnf("PlayerBlobManagerServer:perform_queued_request_get() tar_blob.UserId(%d) ~= queued_request.user_id(%d)", v_u_231.UserId, p_u_220:get_user_id())
                    end)
                    v_u_231.UserId = p_u_220:get_user_id()
                end;
                p_u_52._guild_manager:handle_playerblob_extra(p_u_220:get_user_id(), v_u_228)
                v_u_53:player_blob_verify_action(v_u_231, function(p235) --[[ Line: 934 ]]
                    --[[ Upvalues: (ref 1): v_u_231, (ref 2): v_u_13, (ref 3): v_u_6, (ref 4): v_u_5, (ref 5): v_u_9, (ref 6): v_u_10, (ref 7): v_u_23, (ref 8): p_u_220 ]]
                    v_u_231 = p235
                    v_u_13:validate_playerblob(v_u_231)
                    if v_u_6:is_dev_build() then
                        if v_u_5.PlayerEquipTestGear == true then
                            v_u_9:equip_debug_to_playerblob(v_u_231)
                        end;
                        if v_u_5.AddDebugCraftingMaterialsOnStartup == true then
                            v_u_10:add_debug_materials_to_playerblob(v_u_231)
                        end;
                        if v_u_5.DebugGearSetUpgrades == true then
                            v_u_9:add_debug_gear_upgrades_to_playerblob(v_u_231)
                        end;
                        if v_u_5.DebugAddTestMinis == true then
                            v_u_23:add_debug_pets_to_playerblob(v_u_231)
                        end;
                    end;
                    p_u_220:run_callbacks(v_u_231)
                end)
            end;
        end;
        local function _() --[[ Name: call_web_api_player_get_blob ]] --[[ Line: 958 ]]
            --[[ Upvalues: (ref 1): p_u_52, (copy 2): p_u_220, (ref 3): v_u_1, (ref 4): v_u_221, (ref 5): v_u_222, (copy 6): f_callback_if_all_loaded ]]
            p_u_52._api:api_player_get_blob(p_u_220:get_user_id(), function(p236, p237, p238, p239) --[[ Line: 959 ]]
                --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_221, (ref 3): v_u_222, (ref 4): f_callback_if_all_loaded ]]
                if p236 ~= true then
                    return v_u_1:errf("api_player_get_blob response(%s) err(%s)", tostring(p237), (tostring(p238)));
                end;
                v_u_221 = p237
                v_u_222 = p239
                f_callback_if_all_loaded()
            end)
        end;
        local v_u_240 = ""
        v_u_6:ptry(function() --[[ Line: 970 ]]
            --[[ Upvalues: (ref 1): p_u_52, (copy 2): p_u_220, (ref 3): v_u_240 ]]
            local v241 = p_u_52._id_to_player:contains(p_u_220:get_user_id()) and p_u_52._id_to_player:get(p_u_220:get_user_id())
            if v241 then
                v_u_240 = v241.Name
            end;
        end)
        if v_u_5.PlayerBlobOnlyReadFromDatastore == true then
            p_u_52._guild_manager:get_guild_datastore_manager():dsapi_player_get_blob_guild_data_only(p_u_220:get_user_id(), v_u_240, function(p242, p243) --[[ Line: 980 ]]
                --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_221, (ref 3): v_u_8, (ref 4): v_u_222, (copy 5): f_callback_if_all_loaded ]]
                if p242 ~= true then
                    return v_u_1:errf("api_player_get_blob_guild_data_only response(%s)", (tostring(p243)));
                end;
                v_u_221 = v_u_8:new()
                v_u_222 = p243
                f_callback_if_all_loaded()
            end)
        elseif v_u_5.PlayerBlobWebOnlyReadOnInitialRequest == true then
            if p_u_220:get_request_type() == v_u_33.GetInitial then
                p_u_52._api:api_player_get_blob(p_u_220:get_user_id(), function(p244, p245, p246, p247) --[[ Line: 959 ]]
                    --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_221, (ref 3): v_u_222, (copy 4): f_callback_if_all_loaded ]]
                    if p244 ~= true then
                        return v_u_1:errf("api_player_get_blob response(%s) err(%s)", tostring(p245), (tostring(p246)));
                    end;
                    v_u_221 = p245
                    v_u_222 = p247
                    f_callback_if_all_loaded()
                end)
            else
                p_u_52._guild_manager:get_guild_datastore_manager():dsapi_player_get_blob_guild_data_only(p_u_220:get_user_id(), v_u_240, function(p248, p249) --[[ Line: 992 ]]
                    --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_221, (ref 3): v_u_8, (ref 4): v_u_222, (copy 5): f_callback_if_all_loaded ]]
                    if p248 ~= true then
                        return v_u_1:errf("api_player_get_blob_guild_data_only response(%s)", (tostring(p249)));
                    end;
                    v_u_221 = v_u_8:new()
                    v_u_222 = p249
                    f_callback_if_all_loaded()
                end)
            end;
        else
            p_u_52._api:api_player_get_blob(p_u_220:get_user_id(), function(p250, p251, p252, p253) --[[ Line: 959 ]]
                --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_221, (ref 3): v_u_222, (copy 4): f_callback_if_all_loaded ]]
                if p250 ~= true then
                    return v_u_1:errf("api_player_get_blob response(%s) err(%s)", tostring(p251), (tostring(p252)));
                end;
                v_u_221 = p251
                v_u_222 = p253
                f_callback_if_all_loaded()
            end)
        end;
        v_u_59:get_playerblob_daily_section(p_u_220:get_user_id(), p_u_52._api:get_day_id(), function(p254) --[[ Line: 1004 ]]
            --[[ Upvalues: (ref 1): v_u_223, (copy 2): f_callback_if_all_loaded ]]
            v_u_223 = p254
            f_callback_if_all_loaded()
        end)
        v_u_59:get_playerblob_weekly_section(p_u_220:get_user_id(), p_u_52._api:get_week_id(), function(p255) --[[ Line: 1008 ]]
            --[[ Upvalues: (ref 1): v_u_224, (copy 2): f_callback_if_all_loaded ]]
            v_u_224 = p255
            f_callback_if_all_loaded()
        end)
        v_u_59:get_playerblob_blob(p_u_220:get_user_id(), function(p256, p257) --[[ Line: 1012 ]]
            --[[ Upvalues: (ref 1): v_u_225, (ref 2): v_u_226, (copy 3): f_callback_if_all_loaded ]]
            v_u_225 = p256
            v_u_226 = p257
            f_callback_if_all_loaded()
        end)
    end;
    local function f_perform_queued_request_write(p_u_258) --[[ Name: perform_queued_request_write ]] --[[ Line: 1019 ]]
        --[[ Upvalues: (copy 1): v_u_54, (ref 2): v_u_1, (ref 3): v_u_8, (copy 4): p_u_52, (ref 5): v_u_7, (ref 6): v_u_6, (ref 7): v_u_5, (ref 8): v_u_19, (copy 9): v_u_53, (ref 10): v_u_33, (ref 11): v_u_28, (copy 12): v_u_59, (ref 13): s_HttpService_0, (ref 14): v_u_4 ]]
        if v_u_54:contains(p_u_258:get_user_id()) == false then
            v_u_1:warnf("PlayerBlobManagerServer:perform_queued_request(%d) Write does not have blob", p_u_258:get_user_id())
        else
            local v_u_259 = v_u_54:get(p_u_258:get_user_id())
            if v_u_8:is_banned(v_u_259) then
                return v_u_1:warnf("PlayerBlobManagerServer:perform_queued_request Write player is banned(%s)", (tostring(p_u_258:get_user_id())));
            end;
            local v260, v_u_261 = v_u_8:validate_with_dayid_weekid(v_u_259, p_u_52._api:get_day_id(), p_u_52._api:get_week_id())
            if v260 == true then
                pcall(function() --[[ Line: 1032 ]]
                    --[[ Upvalues: (ref 1): p_u_52, (ref 2): v_u_7, (copy 3): p_u_258, (ref 4): v_u_6, (copy 5): v_u_261, (ref 6): v_u_1 ]]
                    p_u_52._api:api_report_evt(v_u_7.ReportEvt_PlayerblobValidateErrorOnSync, p_u_258:get_user_id(), 0, v_u_6:table_to_string({
                        ["ServerDayID"] = p_u_52._api:get_day_id(),
                        ["SPID"] = p_u_52._api:get_spid(),
                        ["GlobalTime"] = p_u_52._api:get_global_time(),
                        ["Data"] = v_u_261:get_table()
                    }))
                    v_u_1:warnf("Request(Write) PlayerBlob:validate_with_dayid_weekid fail(%s)", v_u_6:table_to_string(v_u_261:get_table()))
                end)
            end;
            local v_u_262 = nil
            local v_u_263 = nil
            local v_u_264 = nil
            local v_u_265 = nil
            local function f_callback_if_all_loaded() --[[ Name: callback_if_all_loaded ]] --[[ Line: 1052 ]]
                --[[ Upvalues: (ref 1): v_u_262, (ref 2): v_u_263, (ref 3): v_u_264, (ref 4): v_u_5, (ref 5): v_u_265, (copy 6): p_u_258, (ref 7): p_u_52, (ref 8): v_u_6, (ref 9): v_u_19, (copy 10): v_u_259, (ref 11): v_u_1, (ref 12): v_u_7, (ref 13): v_u_53, (ref 14): v_u_33, (ref 15): v_u_8 ]]
                if v_u_262 == nil or (v_u_263 == nil or v_u_264 == nil) then
                    return;
                elseif v_u_5.PlayerBlobDatastoreDoWriteBlobToDatastore == true and v_u_265 == nil then
                    return;
                else
                    local v266 = v_u_262
                    if p_u_258:has_guild_contribution() then
                        p_u_52._guild_manager:clear_guildid_cache((p_u_258:get_guild_contribution()))
                        local v267 = p_u_52._player_manager:id_to_player(p_u_258:get_user_id())
                        if v267 then
                            local v268 = p_u_52._chat:get_chat_service()
                            if v266.ContributionPoints ~= nil then
                                v268:send_system_message_to_player_for_channel(v267, v268:get_channel(v268:get_server_system_channel_id()), string.format("You have earned %d contribution points for your team!", (tonumber(v266.ContributionPoints))), function(p269) --[[ Line: 1076 ]]
                                    --[[ Upvalues: (ref 1): v_u_6 ]]
                                    p269:set_channel_name("")
                                    p269:set_icon(v_u_6:get_team_icon())
                                end)
                            end;
                            if v266.DidCapContributionPoints == true then
                                v268:send_system_message_to_player_for_channel(v267, v268:get_channel(v268:get_server_system_channel_id()), string.format("You have hit the weekly limit of contribution points."), function(p270) --[[ Line: 1088 ]]
                                    --[[ Upvalues: (ref 1): v_u_6 ]]
                                    p270:set_channel_name("")
                                    p270:set_icon(v_u_6:get_team_icon())
                                end)
                            end;
                        end;
                    end;
                    v_u_19:is_int(v266.LastModifiedTime)
                    if v266.Ok == true then
                        v_u_259.LastModifiedTime = v266.LastModifiedTime
                        p_u_258:run_callbacks(v_u_259)
                    else
                        local v271 = string.format("api_player_sync_blob web ok fail(%s) player(%s) pre_sync_time(%s) post_sync_time(%s)", tostring(v266.Status), tostring(p_u_258:get_user_id()), tostring(v_u_259.LastModifiedTime), (tostring(v266.LastModifiedTime)))
                        v_u_1:warnf(v271)
                        p_u_52._api:api_report_evt(v_u_7.ReportEvt_ApiPlayerSyncBlobFail, p_u_258:get_user_id(), v266.Status, v271)
                        v_u_53:enqueue_blob_sync_request(p_u_258:get_user_id(), v_u_33.Get, function(p272) --[[ Line: 1107 ]]
                            --[[ Upvalues: (ref 1): v_u_8, (ref 2): v_u_1, (ref 3): p_u_258 ]]
                            if v_u_8:is_banned(p272) then
                                return v_u_1:warnf("sync_blob ok fail is_banned");
                            end;
                            p_u_258:run_callbacks(p272)
                        end, true)
                    end;
                end;
            end;
            local v_u_273 = v_u_28.DailySection:create_from_playerblob(v_u_259)
            v_u_59:write_playerblob_daily_section(p_u_258:get_user_id(), p_u_52._api:get_day_id(), v_u_273, function() --[[ Line: 1115 ]]
                --[[ Upvalues: (ref 1): v_u_263, (copy 2): v_u_273, (copy 3): f_callback_if_all_loaded ]]
                v_u_263 = v_u_273
                f_callback_if_all_loaded()
            end)
            local v_u_274 = v_u_28.WeeklySection:create_from_playerblob(v_u_259)
            v_u_59:write_playerblob_weekly_section(p_u_258:get_user_id(), p_u_52._api:get_week_id(), v_u_274, function() --[[ Line: 1121 ]]
                --[[ Upvalues: (ref 1): v_u_264, (copy 2): v_u_274, (copy 3): f_callback_if_all_loaded ]]
                v_u_264 = v_u_274
                f_callback_if_all_loaded()
            end)
            local v275
            if v_u_5.PlayerBlobDatastoreDoReadComponentsFromDatastore == true and v_u_5.PlayerBlobDatastoreDoReadComponentsFromDatastore_AndDoNotWriteToWeb == true then
                v275 = v_u_8:new()
                v_u_8:update_from_obj(v275, v_u_259)
                v_u_28.DailySection:clear_playerblob(v275)
                v_u_28.WeeklySection:clear_playerblob(v275)
            else
                v275 = v_u_259
            end;
            if v_u_5.PlayerBlobDatastoreDoWriteBlobToDatastore == true then
                v_u_59:write_playerblob_blob(p_u_258:get_user_id(), v_u_259, function(p276, p277) --[[ Line: 1138 ]]
                    --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_265, (copy 3): f_callback_if_all_loaded ]]
                    if not p276 then
                        return v_u_1:errf("_playerblob_datastore_manager:write_playerblob_blob fail");
                    end;
                    v_u_265 = p277
                    f_callback_if_all_loaded()
                end)
            end;
            if v_u_5.PlayerBlobDatastoreWebDoNotWritePlayerBlob == true then
                p_u_52._guild_manager:get_guild_datastore_manager():dsapi_player_sync_guild_data_only(p_u_258:get_user_id(), function(p278) --[[ Line: 1151 ]]
                    --[[ Upvalues: (copy 1): p_u_258 ]]
                    local v279
                    if p_u_258:has_guild_contribution() then
                        local _, v280 = p_u_258:get_guild_contribution()
                        p278.guild_contribution = v280
                        v279 = true
                    else
                        v279 = false
                    end;
                    return v279;
                end, function(_, _, p281) --[[ Line: 1160 ]]
                    --[[ Upvalues: (ref 1): v_u_262, (copy 2): f_callback_if_all_loaded ]]
                    v_u_262 = p281
                    f_callback_if_all_loaded()
                end)
            else
                p_u_52._api:api_player_sync_blob(p_u_258:get_user_id(), s_HttpService_0:JSONEncode(v275), function(p282, p283, p284) --[[ Line: 1166 ]]
                    --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_262, (copy 3): f_callback_if_all_loaded ]]
                    if not p282 then
                        return v_u_1:errf("api_player_sync_blob response(%s)", (tostring(p283)));
                    end;
                    if p284 == nil or typeof(p284.LastModifiedTime) ~= "number" then
                        v_u_1:warnf("success(%s) response(%s)", tostring(p282), (tostring(p283)))
                    end;
                    v_u_262 = p284
                    f_callback_if_all_loaded()
                end, function() --[[ Line: 1177 ]]
                    --[[ Upvalues: (ref 1): p_u_52, (ref 2): v_u_4, (copy 3): p_u_258 ]]
                    p_u_52._evt:fire_event_to_client(v_u_4.EVT_PlayerBlob_ServerRaiseSyncFail, p_u_52._player_manager:id_to_player(p_u_258:get_user_id()))
                end, function(p285) --[[ Line: 1179 ]]
                    --[[ Upvalues: (copy 1): p_u_258 ]]
                    if p_u_258:has_guild_contribution() then
                        local _, v286 = p_u_258:get_guild_contribution()
                        p285.guild_contribution = v286
                    end;
                end)
            end;
        end;
    end;
    local v_u_287 = v_u_26:new()
    local v_u_288 = v_u_26:new()
    v_u_53.perform_queued_request = function(_, p289) --[[ Name: perform_queued_request ]] --[[ Line: 1191 ]]
        --[[ Upvalues: (ref 1): v_u_33, (copy 2): v_u_287, (copy 3): f_perform_queued_request_get, (copy 4): v_u_288, (copy 5): f_perform_queued_request_write, (ref 6): v_u_1 ]]
        local v290 = p289:get_request_type()
        if v290 == v_u_33.Get and true or v290 == v_u_33.GetInitial then
            if v_u_287:is_on_cooldown(p289:get_user_id()) == false then
                f_perform_queued_request_get(p289)
                v_u_287:add_cooldown_to_id(p289:get_user_id(), 0.5)
                return true;
            end;
        else
            if p289:get_request_type() ~= v_u_33.Write then
                v_u_1:warnf("PlayerBlobManagerServer:perform_queued_request() unknown request type(%s)", (tostring(p289:get_request_type())))
                return true;
            end;
            if v_u_288:is_on_cooldown(p289:get_user_id()) == false then
                f_perform_queued_request_write(p289)
                v_u_288:add_cooldown_to_id(p289:get_user_id(), 2)
                return true;
            end;
        end;
        return false;
    end;
    local v_u_291 = v_u_2:new()
    v_u_53.update = function(p_u_292, p_u_293) --[[ Name: update ]] --[[ Line: 1218 ]]
        --[[ Upvalues: (ref 1): v_u_6, (copy 2): v_u_291, (copy 3): v_u_57, (copy 4): v_u_287, (copy 5): v_u_288, (copy 6): v_u_55, (copy 7): v_u_56, (copy 8): v_u_54, (copy 9): v_u_59, (ref 10): v_u_14, (copy 11): v_u_72, (copy 12): v_u_58 ]]
        v_u_6:ptry(function() --[[ Line: 1219 ]]
            --[[ Upvalues: (ref 1): v_u_291, (ref 2): v_u_57, (copy 3): p_u_292, (ref 4): v_u_287, (copy 5): p_u_293, (ref 6): v_u_288 ]]
            v_u_291:clear()
            local v294 = v_u_291
            for v295 = 1, v_u_57:count() do
                local v296 = v_u_57:get(v295)
                if p_u_292:perform_queued_request(v296) then
                    v294:push_back(v296)
                end;
            end;
            for v297 = 1, v294:count() do
                v_u_57:remove(v294:get(v297))
            end;
            v_u_287:update(p_u_293)
            v_u_288:update(p_u_293)
        end)
        v_u_6:ptry(function() --[[ Line: 1238 ]]
            --[[ Upvalues: (ref 1): v_u_291, (ref 2): v_u_55, (ref 3): v_u_56, (ref 4): v_u_54, (ref 5): v_u_59 ]]
            v_u_291:clear()
            local v298 = v_u_291
            for v299, _ in v_u_55:key_itr() do
                if v_u_56:contains(v299) ~= true then
                    v_u_54:remove(v299)
                    v_u_59:remove_playerid(v299)
                    v298:push_back(v299)
                end;
            end;
            for v300 = 1, v298:count() do
                v_u_55:remove(v298:get(v300))
            end;
        end)
        v_u_6:ptry(function() --[[ Line: 1253 ]]
            --[[ Upvalues: (ref 1): v_u_291, (ref 2): v_u_56, (ref 3): v_u_14, (copy 4): p_u_293 ]]
            v_u_291:clear()
            local v301 = v_u_291
            for v302, v303 in v_u_56:key_itr() do
                local v304 = v303 - v_u_14:TimescaleToDeltaTime(p_u_293)
                v_u_56:add(v302, v304)
                if v304 <= 0 then
                    v301:push_back(v302)
                end;
            end;
            for v305 = 1, v301:count() do
                v_u_56:remove(v301:get(v305))
            end;
        end)
        v_u_6:ptry(function() --[[ Line: 1268 ]]
            --[[ Upvalues: (ref 1): v_u_72, (copy 2): p_u_293, (ref 3): v_u_291, (ref 4): v_u_58, (ref 5): v_u_59 ]]
            v_u_72:update(p_u_293)
            v_u_291:clear()
            v_u_58:update(p_u_293)
            v_u_59:update(p_u_293)
        end)
    end;
    return v_u_53;
end;
return v32;
