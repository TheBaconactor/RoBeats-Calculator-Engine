-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:02 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.InputUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPList)
local v4 = require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.PlayerSettings)
local v_u_5 = require(game.ReplicatedStorage.SPChat.Shared.SPChatMessage)
local v_u_6 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
require(game.ReplicatedStorage.Shared.CooldownDelay)
local v_u_7 = require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.Shared.AssertType)
local v_u_8 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_9 = require(game.ReplicatedStorage.LocalShared.FrameIndex)
local v10 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_11 = nil
v10:require_client(function() --[[ Line: 16 ]]
    --[[ Upvalues: (ref 1): v_u_11 ]]
    v_u_11 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
end)
local l_Players_0 = game.Players
local v_u_12 = {
    ["Mode"] = {
        ["None"] = 0,
        ["Low"] = 1,
        ["Medium"] = 2,
        ["High"] = 3,
        ["All"] = 4
    },
    ["CullingType"] = {
        ["NPCs"] = 0,
        ["Players"] = 1,
        ["FollowNPCs"] = 2
    },
    ["CullingPriority"] = {
        ["Low"] = 0,
        ["Normal"] = 1,
        ["High"] = 2
    },
    ["NPC_PRIORITY_FLAG_NAME"] = "Priority",
    ["ManagedCharacter"] = {}
}
local v13 = {
    ["NPCs"] = 0,
    ["Players"] = 1,
    ["FollowNPCs"] = 2
}
local l_NPCs_0 = v13.NPCs
local l_Players_1 = v13.Players
local l_FollowNPCs_0 = v13.FollowNPCs
local v_u_14 = {
    ["Low"] = 0,
    ["Normal"] = 1,
    ["High"] = 2
}
local l_Low_0 = v_u_14.Low
local l_Normal_0 = v_u_14.Normal
local l_High_0 = v_u_14.High
local v_u_15 = nil
local l_None_0 = v_u_12.Mode.None
local v_u_16 = nil
local v_u_17 = nil
local v_u_18 = 0
local v_u_19 = 60
local v_u_20 = v_u_3:new()
local v_u_21 = v_u_3:new()
local v_u_22 = v4:new()
local l_ManagedCharacter_0 = v_u_12.ManagedCharacter
l_ManagedCharacter_0.new = function(_, p23, p_u_24) --[[ Name: new ]] --[[ Line: 72 ]]
    --[[ Upvalues: (copy 1): l_NPCs_0, (copy 2): l_Players_1, (copy 3): l_FollowNPCs_0, (ref 4): v_u_11, (ref 5): v_u_15, (copy 6): l_Normal_0, (copy 7): v_u_12, (copy 8): l_High_0, (copy 9): l_Low_0, (copy 10): v_u_2, (ref 11): v_u_16, (ref 12): v_u_17, (ref 13): v_u_19 ]]
    local v25 = {}
    local v_u_26 = l_NPCs_0
    local v_u_27 = nil
    local v_u_28 = nil
    if typeof(p23) == "Instance" and p23.ClassName == "Player" then
        v_u_26 = l_Players_1
        v_u_27 = p23
        v_u_28 = v_u_27.UserId
    elseif p23.is_follow_npc ~= nil then
        v_u_26 = l_FollowNPCs_0
    end;
    local v_u_29
    if v_u_26 == l_Players_1 then
        v_u_29 = v_u_11:get_lobby_characters_folder()
    elseif v_u_26 == l_FollowNPCs_0 then
        v_u_29 = v_u_15._follow_npc_manager:get_follow_npc_root()
    else
        v_u_29 = v_u_11:get_npc_root()
    end;
    local v_u_30 = l_Normal_0
    if p_u_24:FindFirstChild(v_u_12.NPC_PRIORITY_FLAG_NAME) == nil then
        if v_u_26 == l_FollowNPCs_0 then
            v_u_30 = l_Low_0
        end;
    else
        v_u_30 = l_High_0
    end;
    local v_u_31 = v_u_2:get_character_humanoid(p_u_24)
    local v_u_32
    if v_u_31 then
        v_u_32 = v_u_31.RootPart
    else
        v_u_32 = nil
    end;
    local v_u_33 = Vector3.new()
    local v_u_34
    if v_u_32 then
        v_u_33 = v_u_32.Position
        v_u_34 = true
    else
        v_u_34 = false
    end;
    local v_u_35 = nil
    local l_Parent_0 = p_u_24.Parent
    v25.cons = function(p36) --[[ Name: cons ]] --[[ Line: 118 ]]
        p36:update_cached_position()
        p36:update_cached_visible()
    end;
    v25.update_cached_position = function(_) --[[ Name: update_cached_position ]] --[[ Line: 123 ]]
        --[[ Upvalues: (ref 1): v_u_34, (ref 2): v_u_26, (ref 3): l_Players_1, (ref 4): l_FollowNPCs_0, (ref 5): v_u_31, (ref 6): v_u_2, (copy 7): p_u_24, (ref 8): v_u_32, (ref 9): v_u_33 ]]
        if v_u_34 == false or (v_u_26 == l_Players_1 or v_u_26 == l_FollowNPCs_0) then
            if v_u_31 == nil then
                v_u_31 = v_u_2:get_character_humanoid(p_u_24)
            end;
            if v_u_31 and v_u_32 == nil then
                v_u_32 = v_u_31.RootPart
            end;
            if v_u_32 then
                v_u_33 = v_u_32.Position
                v_u_34 = true
            end;
        end;
    end;
    v25.update_cached_visible = function(p37) --[[ Name: update_cached_visible ]] --[[ Line: 139 ]]
        --[[ Upvalues: (ref 1): v_u_35, (ref 2): l_Parent_0 ]]
        local v38, v39 = p37:is_visible()
        v_u_35 = v38
        l_Parent_0 = v39
    end;
    v25.get_cached_position = function(_) --[[ Name: get_cached_position ]] --[[ Line: 145 ]]
        --[[ Upvalues: (ref 1): v_u_33 ]]
        return v_u_33;
    end;
    v25.get_cached_visible = function(_) --[[ Name: get_cached_visible ]] --[[ Line: 146 ]]
        --[[ Upvalues: (ref 1): v_u_35 ]]
        return v_u_35;
    end;
    v25.get_cached_parent = function(_) --[[ Name: get_cached_parent ]] --[[ Line: 147 ]]
        --[[ Upvalues: (ref 1): l_Parent_0 ]]
        return l_Parent_0;
    end;
    v25.get_type = function(_) --[[ Name: get_type ]] --[[ Line: 149 ]]
        --[[ Upvalues: (ref 1): v_u_26 ]]
        return v_u_26;
    end;
    v25.get_userid = function(_) --[[ Name: get_userid ]] --[[ Line: 150 ]]
        --[[ Upvalues: (ref 1): v_u_28 ]]
        return v_u_28;
    end;
    v25.get_player = function(_) --[[ Name: get_player ]] --[[ Line: 151 ]]
        --[[ Upvalues: (ref 1): v_u_27 ]]
        return v_u_27;
    end;
    v25.is_player = function(_) --[[ Name: is_player ]] --[[ Line: 152 ]]
        --[[ Upvalues: (ref 1): v_u_26, (ref 2): l_Players_1 ]]
        return v_u_26 == l_Players_1;
    end;
    v25.get_character = function(_) --[[ Name: get_character ]] --[[ Line: 153 ]]
        --[[ Upvalues: (copy 1): p_u_24 ]]
        return p_u_24;
    end;
    v25.get_priority = function(_) --[[ Name: get_priority ]] --[[ Line: 154 ]]
        --[[ Upvalues: (ref 1): v_u_30 ]]
        return v_u_30;
    end;
    v25.get_primarypart = function(_) --[[ Name: get_primarypart ]] --[[ Line: 155 ]]
        --[[ Upvalues: (ref 1): v_u_32 ]]
        return v_u_32;
    end;
    local function _() --[[ Name: get_hidden_parent ]] --[[ Line: 157 ]]
        --[[ Upvalues: (ref 1): v_u_26, (ref 2): l_Players_1, (ref 3): v_u_16, (ref 4): v_u_17 ]]
        if v_u_26 == l_Players_1 then
            return v_u_16;
        else
            return v_u_17;
        end;
    end;
    local function _() --[[ Name: get_visible_parent ]] --[[ Line: 164 ]]
        --[[ Upvalues: (ref 1): v_u_29 ]]
        return v_u_29;
    end;
    v25.is_visible = function(_) --[[ Name: is_visible ]] --[[ Line: 166 ]]
        --[[ Upvalues: (copy 1): p_u_24, (ref 2): v_u_29 ]]
        local l_Parent_1 = p_u_24.Parent
        return l_Parent_1 == v_u_29, l_Parent_1;
    end;
    local v_u_40 = 0
    v25.get_visible_update_count = function(_) --[[ Name: get_visible_update_count ]] --[[ Line: 173 ]]
        --[[ Upvalues: (ref 1): v_u_40 ]]
        return v_u_40;
    end;
    v25.increment_visible_update_count = function(_) --[[ Name: increment_visible_update_count ]] --[[ Line: 174 ]]
        --[[ Upvalues: (ref 1): v_u_40 ]]
        v_u_40 = v_u_40 + 1
    end;
    v25.set_visible = function(_, p41) --[[ Name: set_visible ]] --[[ Line: 176 ]]
        --[[ Upvalues: (ref 1): v_u_35, (ref 2): v_u_29, (ref 3): v_u_26, (ref 4): l_Players_1, (ref 5): v_u_16, (ref 6): v_u_17, (ref 7): v_u_40, (copy 8): p_u_24, (ref 9): l_Parent_0 ]]
        if v_u_35 ~= p41 then
            v_u_35 = p41
            local v42
            if p41 then
                v42 = v_u_29
            else
                if v_u_26 == l_Players_1 then
                    v42 = v_u_16
                else
                    v42 = v_u_17
                end;
                v_u_40 = 0
            end;
            p_u_24.Parent = v42
            l_Parent_0 = v42
        end;
    end;
    v25.in_radius = function(p43) --[[ Name: in_radius ]] --[[ Line: 191 ]]
        --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_30, (ref 3): l_Low_0, (ref 4): v_u_19 ]]
        local l_magnitude_0 = (v_u_2:get_localplayer_cframe().Position - p43:get_cached_position()).magnitude
        if v_u_30 == l_Low_0 then
            l_magnitude_0 = l_magnitude_0 * 3
        end;
        return l_magnitude_0 < v_u_19;
    end;
    v25:cons()
    return v25;
end;
v_u_12.initial_setup = function(_, p44) --[[ Name: initial_setup ]] --[[ Line: 207 ]]
    --[[ Upvalues: (ref 1): v_u_15, (ref 2): v_u_16, (ref 3): v_u_17, (copy 4): v_u_12, (copy 5): v_u_6, (copy 6): v_u_7, (copy 7): v_u_21, (copy 8): v_u_22, (copy 9): v_u_2, (ref 10): v_u_11 ]]
    v_u_15 = p44
    v_u_16 = Instance.new("Folder", game.Lighting)
    v_u_16.Name = "CulledCharacters"
    v_u_17 = Instance.new("Folder", game.Lighting)
    v_u_17.Name = "CulledNPCs"
    v_u_12:set_mode(v_u_12.Mode.Medium)
    v_u_15._evt:wait_on_event(v_u_6.EVT_Lobby_ServerNotifySyncCullingDataToPlayer, function(p45) --[[ Line: 217 ]]
        --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_21, (ref 3): v_u_22, (ref 4): v_u_2, (ref 5): v_u_15 ]]
        if p45 == nil then
            return;
        elseif typeof(p45) == "table" then
            if p45.CharactersToSync ~= nil then
                v_u_21:clear()
                v_u_22:clear()
                for _, v46 in pairs(p45.CharactersToSync) do
                    local l_Character_0 = v46.Character
                    local l_CFrame_0 = v46.CFrame
                    if l_Character_0 ~= v_u_2:get_local_character() and v_u_15._follow_npc_manager:is_character_managed_local_character(l_Character_0) ~= true then
                        v_u_21:push_back(l_Character_0)
                        v_u_22:add(l_Character_0, l_CFrame_0)
                    end;
                end;
            end;
        else
            return v_u_7:warnf("EVT_Lobby_ServerNotifySyncCullingDataToPlayer sync_info is not table");
        end;
    end)
    v_u_11:get_lobby_characters_folder().ChildAdded:Connect(function() --[[ Line: 235 ]]
        --[[ Upvalues: (ref 1): v_u_12 ]]
        v_u_12:do_post_update()
    end)
end;
v_u_12.sync_characters_to_cframe = function(_) --[[ Name: sync_characters_to_cframe ]] --[[ Line: 245 ]]
    --[[ Upvalues: (copy 1): v_u_22, (copy 2): v_u_2 ]]
    for v_u_47, v_u_48 in v_u_22:key_itr() do
        v_u_2:ptry(function() --[[ Line: 247 ]]
            --[[ Upvalues: (copy 1): v_u_47, (copy 2): v_u_48 ]]
            v_u_47:SetPrimaryPartCFrame(v_u_48)
        end)
    end;
end;
v_u_12.set_all_managed_characters_visible_and_reset_state = function(_) --[[ Name: set_all_managed_characters_visible_and_reset_state ]] --[[ Line: 253 ]]
    --[[ Upvalues: (copy 1): v_u_20 ]]
    for _, v49 in v_u_20:key_itr() do
        if v49:get_cached_visible() == false then
            v49:set_visible(true)
        end;
    end;
    v_u_20:clear()
end;
v_u_12.get_mode = function(_) --[[ Name: get_mode ]] --[[ Line: 262 ]]
    --[[ Upvalues: (ref 1): l_None_0 ]]
    return l_None_0;
end;
v_u_12.get_radius = function(_) --[[ Name: get_radius ]] --[[ Line: 263 ]]
    --[[ Upvalues: (ref 1): v_u_19 ]]
    return v_u_19;
end;
v_u_12.set_mode = function(_, p50) --[[ Name: set_mode ]] --[[ Line: 264 ]]
    --[[ Upvalues: (ref 1): l_None_0, (copy 2): v_u_12, (ref 3): v_u_18, (ref 4): v_u_19 ]]
    if p50 == l_None_0 then
        return;
    else
        l_None_0 = p50
        if p50 == v_u_12.Mode.None then
            v_u_18 = 0
            v_u_19 = 75
            return;
        elseif p50 == v_u_12.Mode.Low then
            v_u_18 = 10
            v_u_19 = 125
            return;
        elseif p50 == v_u_12.Mode.Medium then
            v_u_18 = 15
            v_u_19 = 150
            return;
        elseif p50 == v_u_12.Mode.High then
            v_u_18 = 30
            v_u_19 = 200
        elseif p50 == v_u_12.Mode.All then
            v_u_18 = 150
            v_u_19 = 500
        end;
    end;
end;
local v_u_51 = v4:new()
local v_u_52 = v4:new()
local v_u_53 = v4:new()
local v_u_54 = v4:new()
local v_u_55 = v4:new()
local function f_debug_log_managed_characters() --[[ Name: debug_log_managed_characters ]] --[[ Line: 291 ]]
    --[[ Upvalues: (copy 1): v_u_20, (copy 2): v_u_55, (copy 3): v_u_2, (copy 4): v_u_14, (copy 5): v_u_7 ]]
    for v56 = 1, v_u_20:count() do
        local v57 = v_u_20:get(v56)
        v_u_7:puts((string.format("\t#%d (%s) Pri[%s] Vis[%s] = %.2f", v56, v57:get_character():GetFullName(), v_u_2:enum_val_to_name(v57:get_priority(), v_u_14), tostring(v57:is_visible()), not v_u_55:contains(v57) and -1 or v_u_55:get(v57))))
    end;
end;
local function f_update_character_culling(p58) --[[ Name: update_character_culling ]] --[[ Line: 311 ]]
    --[[ Upvalues: (ref 1): v_u_11, (copy 2): v_u_2, (copy 3): l_Players_0, (copy 4): v_u_51, (copy 5): v_u_52, (copy 6): v_u_53, (copy 7): v_u_20, (copy 8): l_FollowNPCs_0, (copy 9): l_ManagedCharacter_0, (copy 10): v_u_54, (copy 11): v_u_55, (copy 12): l_Low_0, (copy 13): v_u_3, (copy 14): l_High_0, (ref 15): v_u_18, (copy 16): v_u_8, (copy 17): v_u_7, (copy 18): f_debug_log_managed_characters, (copy 19): v_u_21, (copy 20): v_u_22 ]]
    local v59 = v_u_11:is_mode_lobby()
    v_u_2:profilebegin("update_character_culling")
    v_u_2:profilebegin("setup")
    local v60 = l_Players_0:GetPlayers()
    local v61 = v_u_11:get_npc_root():GetChildren()
    v_u_51:clear()
    v_u_52:clear()
    v_u_53:clear()
    for v62 = 1, v_u_20:count() do
        local v63 = v_u_20:get(v62)
        if v63:is_player() then
            v_u_51:add(v63:get_userid(), v63)
        elseif v63:get_type() == l_FollowNPCs_0 then
            v_u_53:add(v63:get_character(), v63)
        else
            v_u_52:add(v63:get_character(), v63)
        end;
    end;
    v_u_2:profileend()
    if v59 then
        v_u_2:profilebegin("ManagedCharacter create new (NPC)")
        for _, v64 in pairs(v61) do
            if v_u_52:contains(v64) ~= true then
                local v65 = l_ManagedCharacter_0:new({
                    ["Name"] = v64.Name
                }, v64)
                v_u_20:push_back(v65)
                v_u_52:add(v64, v65)
            end;
        end;
        v_u_2:profileend()
        v_u_2:profilebegin("ManagedCharacter create new (Players)")
        for _, v66 in pairs(v60) do
            local l_UserId_0 = v66.UserId
            if l_UserId_0 ~= v_u_2:get_local_userid() then
                local l_Character_1 = v66.Character
                if l_Character_1 ~= nil and v_u_51:contains(l_UserId_0) ~= true then
                    local v67 = l_ManagedCharacter_0:new(v66, l_Character_1)
                    v_u_20:push_back(v67)
                    v_u_51:add(l_UserId_0, v67)
                end;
            end;
        end;
        v_u_2:profileend()
        v_u_2:profilebegin("ManagedCharacter create new (FollowNPC)")
        for v68 = 1, p58._follow_npc_manager:get_active_follow_npcs():count() do
            local v69 = p58._follow_npc_manager:get_active_follow_npcs():get(v68)
            if v69:is_local_character() ~= true then
                local v70 = v69:get_npc_character()
                if v_u_53:contains(v70) ~= true then
                    local v71 = l_ManagedCharacter_0:new(v69, v70)
                    v_u_20:push_back(v71)
                    v_u_53:add(v70, v71)
                end;
            end;
        end;
        v_u_2:profileend()
    end;
    v_u_2:profilebegin("_managed_characters:update_cached")
    for v72 = 1, v_u_20:count() do
        local v73 = v_u_20:get(v72)
        v73:update_cached_position()
        v73:update_cached_visible()
    end;
    v_u_2:profileend()
    v_u_2:profilebegin("_managed_characters:remove_if")
    v_u_20:remove_if(function(p74) --[[ Line: 385 ]]
        --[[ Upvalues: (ref 1): v_u_51 ]]
        local v75
        if p74:is_player() and (p74:get_player() == nil or (p74:get_character() == nil or (v_u_51:contains(p74:get_userid()) ~= true or p74:get_cached_parent() == nil))) then
            v75 = true
        elseif p74:is_player() == true then
            v75 = false
        else
            v75 = p74:get_cached_parent() == nil and true or p74:get_character() == nil
        end;
        return v75;
    end)
    v_u_2:profileend()
    v_u_54:clear()
    for v76 = 1, v_u_20:count() do
        local v77 = v_u_20:get(v76)
        v_u_54:add(v77:get_character(), v77)
    end;
    if v59 then
        v_u_2:profilebegin("_managed_characters sort")
        local l_Position_0 = v_u_2:get_localplayer_cframe().Position
        v_u_55:clear()
        for v78 = 1, v_u_20:count() do
            local v79 = v_u_20:get(v78)
            local l_Magnitude_0 = (l_Position_0 - v79:get_cached_position()).Magnitude
            if v79:get_priority() == l_Low_0 then
                l_Magnitude_0 = l_Magnitude_0 * 3
            end;
            v_u_55:add(v79, l_Magnitude_0)
        end;
        v_u_3:sort_fast(v_u_20, function(p80, p81) --[[ Line: 422 ]]
            --[[ Upvalues: (ref 1): v_u_55 ]]
            return v_u_55:get(p80) < v_u_55:get(p81);
        end)
        v_u_2:profileend()
    end;
    v_u_2:profilebegin("_managed_characters foreach set_visible")
    local v82 = 0
    local v83 = 0
    for v84 = 1, v_u_20:count() do
        local v85 = v_u_20:get(v84)
        local v86 = v85:get_priority()
        local v87 = v85:get_cached_visible()
        local v88
        if v86 == l_High_0 or v82 < v_u_18 then
            v88 = v85:in_radius()
        else
            v88 = false
        end;
        if v87 ~= v88 then
            if v_u_8.DoLogOnCharacterCullingUpdate == true and v_u_2:is_dev_build() then
                v_u_7:puts("[%d] set_visible(%s) on: %s", v82, tostring(v88), v85:get_character():GetFullName())
                f_debug_log_managed_characters()
            end;
            v85:set_visible(v88)
            v83 = v83 + 1
        end;
        if v88 then
            v82 = v82 + 1
        end;
        if v83 >= 2 then
            break;
        end;
    end;
    v_u_2:profileend()
    if v59 then
        v_u_2:profilebegin("update_cached_player_position_data")
        if v_u_21:count() > 0 then
            local v89 = v_u_21:pop_back()
            if v89 ~= nil and (v89.PrimaryPart ~= nil and v_u_54:contains(v89)) then
                local v90 = v_u_54:get(v89)
                if v90:get_cached_visible() ~= true or v90:get_visible_update_count() < 1 then
                    v89:SetPrimaryPartCFrame((v_u_22:get(v89)))
                    v90:update_cached_position()
                    if v90:get_cached_visible() == true then
                        v90:increment_visible_update_count()
                    end;
                end;
            end;
        end;
        v_u_2:profileend()
    end;
    v_u_2:profileend()
end;
v_u_12.character_of_distance_and_priority_would_be_visible = function(_, p91, p92) --[[ Name: character_of_distance_and_priority_would_be_visible ]] --[[ Line: 481 ]]
    --[[ Upvalues: (copy 1): l_Normal_0, (copy 2): l_High_0, (ref 3): v_u_19, (copy 4): l_Low_0, (copy 5): v_u_20, (copy 6): v_u_55, (ref 7): v_u_18 ]]
    if p92 == nil then
        p92 = l_Normal_0
    end;
    if p92 == l_High_0 then
        return p91 <= v_u_19;
    end;
    if p92 == l_Low_0 then
        p91 = p91 * 3
    end;
    local v93 = p91 + 99999
    local v94 = 0
    local v95 = true
    for v96 = 1, v_u_20:count() do
        local v97 = v_u_20:get(v96)
        local v98 = v_u_19
        if v_u_55:contains(v97) then
            v98 = v_u_55:get(v97)
        end;
        if p91 < v93 and v98 <= p91 then
            local v99
            if v94 < v_u_18 then
                v99 = p91 <= v_u_19
            else
                v99 = false
            end;
            return v99;
        end;
        local v100
        if v97:get_priority() == l_High_0 or v94 < v_u_18 then
            v100 = v97:in_radius()
        else
            v100 = false
        end;
        if v100 then
            v94 = v94 + 1
            v93 = v98
        else
            v93 = v98
        end;
    end;
    return v95;
end;
v_u_12.remove_managed_character = function(_, p_u_101) --[[ Name: remove_managed_character ]] --[[ Line: 516 ]]
    --[[ Upvalues: (copy 1): v_u_20 ]]
    local v_u_102 = false
    v_u_20:remove_if(function(p103) --[[ Line: 518 ]]
        --[[ Upvalues: (copy 1): p_u_101, (ref 2): v_u_102 ]]
        local v104 = p_u_101 == p103:get_character()
        if v104 then
            v_u_102 = true
        end;
        return v104;
    end)
    return v_u_102;
end;
local l_CharacterCulling_0 = v_u_9.Test.CharacterCulling
v_u_12.update = function(_, p105, _) --[[ Name: update ]] --[[ Line: 529 ]]
    --[[ Upvalues: (copy 1): v_u_9, (copy 2): l_CharacterCulling_0, (copy 3): v_u_2, (copy 4): f_update_character_culling, (copy 5): v_u_1, (copy 6): v_u_51, (copy 7): v_u_52, (copy 8): v_u_53, (ref 9): v_u_18, (ref 10): v_u_19, (copy 11): v_u_21, (copy 12): v_u_22, (copy 13): v_u_5, (copy 14): v_u_7, (copy 15): f_debug_log_managed_characters ]]
    local v106 = v_u_9:singleton()
    if v106:should_run(l_CharacterCulling_0) ~= false then
        local v107 = v106:get_test_state(l_CharacterCulling_0)
        v107:get_dt_scale()
        p105._input:set_frame_index_state(v107)
        v_u_2:profilebegin("CharacterCulling:update")
        f_update_character_culling(p105)
        v_u_2:profileend()
        if v_u_2:is_dev_build() and (p105._input:control_just_pressed(v_u_1.KEY_DEBUG_4) and p105._menus:top_menu_swallows_input() == false) then
            local v108 = 0
            for _, v109 in v_u_51:key_itr() do
                if v109:is_visible() then
                    v108 = v108 + 1
                end;
            end;
            local v110 = 0
            for _, v111 in v_u_52:key_itr() do
                if v111:is_visible() then
                    v110 = v110 + 1
                end;
            end;
            local v112 = 0
            for _, v113 in v_u_53:key_itr() do
                if v113:is_visible() then
                    v112 = v112 + 1
                end;
            end;
            local v114 = string.format("---\nCharacterCulling info _managed_characters(Players: (%d/%d), NPCs: (%d/%d) FollowNPC: (%d/%d)) _limit_of_characters(%d) _radius(%d) _characters_to_sync(%d) last(%d)", v108, v_u_51:count(), v110, v_u_52:count(), v112, v_u_53:count(), v_u_18, v_u_19, v_u_21:count(), v_u_22:count())
            p105._chat:get_system_channel():add_message_to_channel(v_u_5:new(v114))
            v_u_7:puts(v114)
            f_debug_log_managed_characters()
        end;
        p105._input:set_frame_index_state(nil)
    end;
end;
local v_u_115 = false
v_u_12.do_post_update = function(_) --[[ Name: do_post_update ]] --[[ Line: 586 ]]
    --[[ Upvalues: (ref 1): v_u_115 ]]
    v_u_115 = true
end;
v_u_12.post_update = function(_, p116) --[[ Name: post_update ]] --[[ Line: 587 ]]
    --[[ Upvalues: (ref 1): v_u_115, (copy 2): f_update_character_culling ]]
    if v_u_115 == true then
        f_update_character_culling(p116)
        v_u_115 = false
    end;
end;
v_u_12.get_player_count = function(_) --[[ Name: get_player_count ]] --[[ Line: 594 ]]
    --[[ Upvalues: (copy 1): v_u_51 ]]
    return v_u_51:count();
end;
v_u_12.get_npc_count = function(_) --[[ Name: get_npc_count ]] --[[ Line: 595 ]]
    --[[ Upvalues: (copy 1): v_u_52 ]]
    return v_u_52:count();
end;
v_u_12.get_follow_npc_count = function(_) --[[ Name: get_follow_npc_count ]] --[[ Line: 596 ]]
    --[[ Upvalues: (copy 1): v_u_53 ]]
    return v_u_53:count();
end;
return v_u_12;
