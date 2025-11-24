-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:17 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_2 = require(game.ReplicatedStorage.Server.EnvironmentSetupServer)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_4 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_6 = require(game.ReplicatedStorage.Pets.PetDatabase)
require(game.ReplicatedStorage.Shared.AssertType)
local v_u_7 = require(game.ReplicatedStorage.Pets.PetUtils)
local v_u_8 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_9 = require(game.ReplicatedStorage.Shared.Constants)
local v_u_10 = require(game.ReplicatedStorage.Shared.CooldownDelay)
local v_u_11 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_12 = require(game.ReplicatedStorage.Pets.PetInfoBase)
local v13 = {}
local v_u_14 = v_u_8:new():add_set_from_table_list({ game.Workspace })
local v_u_27 = {
    ["new"] = function(_, p_u_15, _, p_u_16, p_u_17, p_u_18, p_u_19, p_u_20, p_u_21) --[[ Name: new ]] --[[ Line: 20 ]]
        --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_14 ]]
        local v22 = {}
        local function _() end;
        v22.get_npc_character = function(_) --[[ Name: get_npc_character ]] --[[ Line: 35 ]]
            --[[ Upvalues: (ref 1): p_u_19 ]]
            return p_u_19;
        end;
        v22.should_remove = function(_) --[[ Name: should_remove ]] --[[ Line: 37 ]]
            --[[ Upvalues: (copy 1): p_u_17, (ref 2): v_u_3, (ref 3): v_u_14, (copy 4): p_u_15, (copy 5): p_u_16 ]]
            return (p_u_17 == nil or v_u_3:is_child_of_parent_set(p_u_17, v_u_14) ~= true) and true or p_u_15._player_manager:id_to_player(p_u_16) == nil;
        end;
        v22.should_remove_if_playerid_resetting = function(_, p23) --[[ Name: should_remove_if_playerid_resetting ]] --[[ Line: 41 ]]
            --[[ Upvalues: (copy 1): p_u_16 ]]
            return p23 == p_u_16;
        end;
        local v_u_24 = false
        v22.flag_as_network_owner_transferred = function(_) --[[ Name: flag_as_network_owner_transferred ]] --[[ Line: 46 ]]
            --[[ Upvalues: (ref 1): v_u_24 ]]
            v_u_24 = true
        end;
        v22.do_remove = function(_) --[[ Name: do_remove ]] --[[ Line: 50 ]]
            --[[ Upvalues: (ref 1): p_u_21, (ref 2): p_u_19, (copy 3): p_u_20, (ref 4): v_u_24, (ref 5): v_u_3, (copy 6): p_u_15, (copy 7): p_u_18, (copy 8): p_u_16 ]]
            if p_u_21 then
                p_u_21:Destroy()
            end;
            p_u_21 = nil
            if p_u_19 then
                if p_u_20 and v_u_24 then
                    v_u_3:ptry(function() --[[ Line: 57 ]]
                        --[[ Upvalues: (ref 1): v_u_3, (ref 2): p_u_19 ]]
                        v_u_3:r_set_basepart_fn(p_u_19, function(p25) --[[ Line: 58 ]]
                            p25:SetNetworkOwner(nil)
                        end)
                        v_u_3:r_set_basepart_fn(p_u_19, function(p26) --[[ Line: 61 ]]
                            p26.Anchored = true
                        end)
                    end)
                    p_u_15._player_model_cache:store_lobby_petnpc_character(p_u_18, p_u_19, p_u_16)
                else
                    p_u_19:Destroy()
                end;
            end;
            p_u_19 = nil
        end;
        v22.update = function(_, _) --[[ Name: update ]] --[[ Line: 75 ]]
            --[[ Upvalues: (copy 1): p_u_20 ]]
            if p_u_20 and p_u_20:GetState() ~= Enum.HumanoidStateType.Running then
                p_u_20:ChangeState(Enum.HumanoidStateType.Running)
            end;
        end;
        v22.get_info_table = function(_) --[[ Name: get_info_table ]] --[[ Line: 81 ]]
            --[[ Upvalues: (copy 1): p_u_16, (copy 2): p_u_17, (copy 3): p_u_18, (ref 4): p_u_19 ]]
            return {
                ["PlayerID"] = p_u_16,
                ["PlayerCharacter"] = p_u_17,
                ["PetID"] = p_u_18,
                ["NPCCharacter"] = p_u_19
            };
        end;
        return v22;
    end
}
v13.new = function(_, p_u_28) --[[ Name: new ]] --[[ Line: 94 ]]
    --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_11, (copy 3): v_u_8, (copy 4): v_u_6, (copy 5): v_u_4, (copy 6): v_u_3, (copy 7): v_u_9, (copy 8): v_u_2, (copy 9): v_u_12, (copy 10): v_u_27, (copy 11): v_u_10, (copy 12): v_u_7, (copy 13): v_u_1 ]]
    local v_u_29 = {}
    local v_u_30 = v_u_5:new()
    v_u_29.get_active_follow_npcs = function(_) --[[ Name: get_active_follow_npcs ]] --[[ Line: 98 ]]
        --[[ Upvalues: (copy 1): v_u_30 ]]
        return v_u_30;
    end;
    local function _() --[[ Name: cons ]] --[[ Line: 100 ]]
        --[[ Upvalues: (copy 1): p_u_28, (ref 2): v_u_11, (ref 3): v_u_5, (ref 4): v_u_8, (copy 5): v_u_30 ]]
        p_u_28._evt:wait_on_event(v_u_11.EVT_Lobby_ClientRequestInfoForCharacters, function(p31, p32) --[[ Line: 101 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_8, (ref 3): v_u_30, (ref 4): p_u_28, (ref 5): v_u_11 ]]
            local v33 = v_u_5:new()
            local v34 = v_u_8:new()
            v34:add_set_from_table_list(p32)
            for _, v35 in v_u_30:key_itr() do
                if v34:contains(v35:get_npc_character()) and v35:should_remove() ~= true then
                    v33:push_back(v35:get_info_table())
                end;
            end;
            p_u_28._evt:fire_event_to_client(v_u_11.EVT_Lobby_ServerNotifyFollowNPCCreate, p31, v33:get_table())
        end)
    end;
    local function f_create_neu_npc_from_pet_id(p_u_36, p_u_37, p_u_38, p_u_39) --[[ Name: create_neu_npc_from_pet_id ]] --[[ Line: 120 ]]
        --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_4, (ref 3): v_u_3, (ref 4): v_u_9, (ref 5): v_u_2, (ref 6): v_u_12, (copy 7): p_u_28, (ref 8): v_u_11, (ref 9): v_u_27, (copy 10): v_u_29, (copy 11): v_u_30 ]]
        if v_u_6:singleton():contains_petid(p_u_38) == true then
            local _, v_u_40, _ = v_u_3:get_character_parts(p_u_37)
            if v_u_40 == nil then
                return;
            else
                local l_Attachment_0 = Instance.new("Attachment")
                l_Attachment_0.Name = v_u_9.PET_FOLLOW_ATTACHMENT_NAME
                l_Attachment_0.Position = Vector3.new(0, -2.257, 3.5)
                l_Attachment_0.Parent = v_u_40
                local function f_fn_post_create(p41) --[[ Name: fn_post_create ]] --[[ Line: 139 ]]
                    --[[ Upvalues: (copy 1): p_u_36, (copy 2): p_u_37, (ref 3): v_u_4, (ref 4): v_u_3, (ref 5): v_u_2, (copy 6): v_u_40, (copy 7): l_Attachment_0 ]]
                    if p_u_36 == nil or p_u_37 == nil then
                        return v_u_4:warnf("FnPostCreate1");
                    end;
                    local v_u_42, v43, v44 = v_u_3:get_character_parts(p41)
                    if v_u_42 == nil or (v43 == nil or v44 == nil) then
                        return v_u_4:warnf("FnPostCreate2");
                    end;
                    v_u_3:flag_all_objects_as_present_in_source(p41)
                    v_u_2:get_player_collision_group():add_to_group(p41)
                    v_u_3:r_set_basepart_fn(p41, function(p45) --[[ Line: 148 ]]
                        p45.Anchored = true
                        p45.Massless = true
                    end)
                    v_u_3:ptry(function() --[[ Line: 153 ]]
                        --[[ Upvalues: (copy 1): v_u_42 ]]
                        v_u_42:SetStateEnabled(Enum.HumanoidStateType.FallingDown, false)
                        v_u_42:SetStateEnabled(Enum.HumanoidStateType.Ragdoll, false)
                        v_u_42.AutoRotate = false
                    end)
                    p41:SetPrimaryPartCFrame(v_u_40.CFrame + (v_u_40.CFrame - v_u_40.CFrame.p) * Vector3.new(0, -2.257, 3.5) + Vector3.new(0, 0.75, 0))
                    v43.CustomPhysicalProperties = PhysicalProperties.new(5, 0, 0, 0, 0)
                    local l_AlignPosition_0 = Instance.new("AlignPosition")
                    l_AlignPosition_0.Mode = Enum.PositionAlignmentMode.TwoAttachment
                    l_AlignPosition_0.Attachment0 = v44
                    l_AlignPosition_0.Attachment1 = l_Attachment_0
                    l_AlignPosition_0.MaxForce = 60
                    l_AlignPosition_0.MaxVelocity = 16
                    l_AlignPosition_0.Responsiveness = 40
                    l_AlignPosition_0.ApplyAtCenterOfMass = true
                    l_AlignPosition_0.Parent = v43
                    local l_AlignOrientation_0 = Instance.new("AlignOrientation")
                    l_AlignOrientation_0.Mode = Enum.OrientationAlignmentMode.TwoAttachment
                    l_AlignOrientation_0.Attachment0 = v44
                    l_AlignOrientation_0.Attachment1 = l_Attachment_0
                    l_AlignOrientation_0.MaxTorque = 40
                    l_AlignOrientation_0.Responsiveness = 40
                    l_AlignOrientation_0.PrimaryAxisOnly = true
                    l_AlignOrientation_0.Parent = v43
                end;
                local function f_fn_finished_callback(p_u_46, _) --[[ Name: fn_finished_callback ]] --[[ Line: 193 ]]
                    --[[ Upvalues: (copy 1): p_u_36, (copy 2): p_u_37, (ref 3): v_u_4, (ref 4): v_u_3, (ref 5): v_u_12, (ref 6): p_u_28, (ref 7): v_u_11, (ref 8): v_u_27, (ref 9): v_u_29, (copy 10): p_u_38, (copy 11): l_Attachment_0, (ref 12): v_u_30, (copy 13): p_u_39 ]]
                    local function _() --[[ Name: cleanup_character ]] --[[ Line: 194 ]]
                        --[[ Upvalues: (copy 1): p_u_46 ]]
                        p_u_46:Destroy()
                    end;
                    if p_u_36 == nil or p_u_37 == nil then
                        p_u_46:Destroy()
                        return v_u_4:warnf("ServerLobbyFollowNPCManager:create_neu_npc_from_pet_id player or player_character nil");
                    end;
                    local v47, v48, v49 = v_u_3:get_character_parts(p_u_46)
                    if v47 == nil or (v48 == nil or v49 == nil) then
                        p_u_46:Destroy()
                        return v_u_4:warnf("ServerLobbyFollowNPCManager:create_neu_npc_from_pet_id neu_npc_character humanoid, root_part or rig root attachment nil");
                    end;
                    local v_u_50 = nil
                    spawn(function() --[[ Line: 207 ]]
                        --[[ Upvalues: (copy 1): p_u_46, (ref 2): p_u_36, (ref 3): v_u_4, (ref 4): v_u_3, (ref 5): v_u_12, (ref 6): p_u_28, (ref 7): v_u_11, (ref 8): v_u_50 ]]
                        wait(0.25)
                        if p_u_46 == nil or (p_u_46.PrimaryPart == nil or p_u_36 == nil) then
                            return v_u_4:warnf("ServerLobbyFollowNPCManager spawn character or player nil");
                        end;
                        v_u_3:r_set_basepart_fn(p_u_46, function(p51) --[[ Line: 212 ]]
                            p51.Anchored = false
                        end)
                        v_u_3:r_set_basepart_fn(p_u_46, function(p52) --[[ Line: 215 ]]
                            --[[ Upvalues: (ref 1): p_u_36 ]]
                            p52:SetNetworkOwner(p_u_36)
                        end)
                        p_u_46.PrimaryPart.Size = v_u_12:get_default_pet_root_part_size()
                        p_u_28._evt:fire_event_to_client(v_u_11.EVT_Lobby_ServerNotifyTransferNPCNetworkOwnership, p_u_36, p_u_46)
                        if v_u_50 then
                            v_u_50:flag_as_network_owner_transferred()
                        end;
                        if v_u_3:is_dev_build() then
                            v_u_4:puts("Setting follow npc(%s) network owner(%s)", p_u_46.Name, p_u_36.Name)
                        end;
                    end)
                    v_u_50 = v_u_27:new(p_u_28, v_u_29, p_u_36.UserId, p_u_37, p_u_38, p_u_46, v47, l_Attachment_0)
                    v_u_30:push_back(v_u_50)
                    p_u_39(v_u_50)
                end;
                local v_u_53 = p_u_28._player_model_cache:load_stored_lobby_petnpc(p_u_38)
                if v_u_53 then
                    if v_u_3:is_dev_build() then
                        v_u_4:puts("ServerLobbyFollowNPCManager:create_neu_npc_from_pet_id using cached pet(%d)", p_u_38)
                    end;
                    v_u_53.Parent = v_u_2:get_lobby_follow_npcs_folder()
                    f_fn_post_create(v_u_53)
                    spawn(function() --[[ Line: 254 ]]
                        --[[ Upvalues: (copy 1): f_fn_finished_callback, (copy 2): v_u_53 ]]
                        f_fn_finished_callback(v_u_53, v_u_53)
                    end)
                else
                    if v_u_3:is_dev_build() then
                        v_u_4:puts("ServerLobbyFollowNPCManager:create_neu_npc_from_pet_id creating new pet(%d)", p_u_38)
                    end;
                    v_u_6:singleton():get_data_for_petid(p_u_38):create_character({
                        ["WaitBeforeFinish"] = true,
                        ["FnPostCreate"] = f_fn_post_create
                    }, v_u_2:get_lobby_follow_npcs_folder(), f_fn_finished_callback)
                end;
            end;
        else
            return v_u_4:warnf("ServerLobbyFollowNPCManager petid not found(%s)", (tostring(p_u_38)));
        end;
    end;
    local v_u_54 = v_u_10:new()
    local function f_create_player_character_follow_npcs(p55, p56) --[[ Name: create_player_character_follow_npcs ]] --[[ Line: 276 ]]
        --[[ Upvalues: (copy 1): v_u_54, (ref 2): v_u_4, (copy 3): p_u_28, (ref 4): v_u_7, (copy 5): f_create_neu_npc_from_pet_id, (ref 6): v_u_11 ]]
        if v_u_54:is_on_cooldown(p55.UserId) then
            return v_u_4:warnf("ServerLobbyFollowNPCManager:create_player_character_follow_npcs cooldown(%d)", p55.UserId);
        end;
        v_u_54:add_cooldown_to_id(p55.UserId, 1.5)
        local v57, _, v58 = v_u_7:playerblob_get_display_ownedid_petid((p_u_28._player_blob_manager:get_cached_blob(p55.UserId)))
        if v57 then
            f_create_neu_npc_from_pet_id(p55, p56, v58, function(p59) --[[ Line: 289 ]]
                --[[ Upvalues: (ref 1): v_u_4, (ref 2): p_u_28, (ref 3): v_u_11 ]]
                if p59:get_npc_character() == nil then
                    return v_u_4:warnf("EVT_Lobby_ServerNotifyFollowNPCCreate neu_follow_npc get_npc_character is nil");
                end;
                for _, v60 in p_u_28._player_manager:players_key_itr() do
                    p_u_28._evt:fire_event_to_client(v_u_11.EVT_Lobby_ServerNotifyFollowNPCCreate, v60, { p59:get_info_table() })
                end;
            end)
        end;
    end;
    v_u_29.on_player_spawned_to_lobby = function(_, p61, p62) --[[ Name: on_player_spawned_to_lobby ]] --[[ Line: 305 ]]
        --[[ Upvalues: (ref 1): v_u_1, (copy 2): f_create_player_character_follow_npcs ]]
        if v_u_1.DebugMinisActive == true then
            f_create_player_character_follow_npcs(p61, p62)
        end;
    end;
    v_u_29.on_player_reset = function(_, p63, p64) --[[ Name: on_player_reset ]] --[[ Line: 311 ]]
        --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_5, (copy 3): v_u_30, (copy 4): f_create_player_character_follow_npcs ]]
        if v_u_1.DebugMinisActive == true then
            local l_UserId_0 = p63.UserId
            v_u_5:remove_if(v_u_30, function(p65) --[[ Line: 315 ]]
                --[[ Upvalues: (copy 1): l_UserId_0 ]]
                local v66 = p65:should_remove_if_playerid_resetting(l_UserId_0)
                if v66 then
                    p65:do_remove()
                end;
                return v66;
            end)
            f_create_player_character_follow_npcs(p63, p64)
        end;
    end;
    v_u_29.update = function(_, p_u_67) --[[ Name: update ]] --[[ Line: 326 ]]
        --[[ Upvalues: (ref 1): v_u_1, (copy 2): v_u_54, (ref 3): v_u_5, (copy 4): v_u_30 ]]
        if v_u_1.DebugMinisActive == true then
            v_u_54:update(p_u_67)
            v_u_5:for_each(v_u_30, function(p68) --[[ Line: 329 ]]
                --[[ Upvalues: (copy 1): p_u_67 ]]
                p68:update(p_u_67)
            end)
            v_u_5:remove_if(v_u_30, function(p69) --[[ Line: 332 ]]
                local v70 = p69:should_remove()
                if v70 then
                    p69:do_remove()
                end;
                return v70;
            end)
        end;
    end;
    p_u_28._evt:wait_on_event(v_u_11.EVT_Lobby_ClientRequestInfoForCharacters, function(p71, p72) --[[ Line: 101 ]]
        --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_8, (copy 3): v_u_30, (copy 4): p_u_28, (ref 5): v_u_11 ]]
        local v73 = v_u_5:new()
        local v74 = v_u_8:new()
        v74:add_set_from_table_list(p72)
        for _, v75 in v_u_30:key_itr() do
            if v74:contains(v75:get_npc_character()) and v75:should_remove() ~= true then
                v73:push_back(v75:get_info_table())
            end;
        end;
        p_u_28._evt:fire_event_to_client(v_u_11.EVT_Lobby_ServerNotifyFollowNPCCreate, p71, v73:get_table())
    end)
    return v_u_29;
end;
return v13;
