-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:15 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Server.DebugOut)
local v_u_3 = require(game.ReplicatedStorage.Avatar.SanitizeCharacter)
local v_u_4 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_5 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_6 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_7 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_8 = require(game.ReplicatedStorage.Shared.SPMultiDict)
local v_u_9 = require(game.ReplicatedStorage.Server.EnvironmentSetupServer)
local _ = game:GetService("CollectionService")
return {
    ["new"] = function(_, p_u_10, p_u_11) --[[ Name: new ]] --[[ Line: 15 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_6, (copy 3): v_u_5, (copy 4): v_u_2, (copy 5): v_u_4, (copy 6): v_u_3, (copy 7): v_u_9, (copy 8): v_u_8, (copy 9): v_u_7 ]]
        local v12 = {}
        local v_u_13 = v_u_1:new()
        local v_u_14 = v_u_1:new()
        local l_Folder_0 = Instance.new("Folder")
        l_Folder_0.Name = "StoredLobbyCharacter"
        l_Folder_0.Parent = game.ReplicatedStorage
        local v_u_15 = nil
        local v_u_16 = nil
        v_u_6:ptry(function() --[[ Line: 26 ]]
            --[[ Upvalues: (ref 1): v_u_15, (ref 2): v_u_16 ]]
            v_u_15 = game.ReplicatedStorage.Events.LobbyCharacterStoredDoCleanup
            v_u_16 = game.ReplicatedStorage.Events.LobbyPetNPCStoredDoCleanup
        end)
        v12.remove_id_from_cache = function(_, p17) --[[ Name: remove_id_from_cache ]] --[[ Line: 32 ]]
            --[[ Upvalues: (copy 1): v_u_13, (copy 2): v_u_14 ]]
            if v_u_13:contains(p17) then
                local v18 = v_u_13:get(p17)
                v_u_13:remove(p17)
                v18:Destroy()
            end;
            if v_u_14:contains(p17) then
                local v19 = v_u_14:get(p17)
                v_u_14:remove(p17)
                v19:Destroy()
            end;
        end;
        local function _(p20) --[[ Name: destroy_player_character ]] --[[ Line: 45 ]]
            if p20.Character ~= nil then
                p20.Character:Destroy()
                p20.Character = nil
            end;
        end;
        local function _(p_u_21) --[[ Name: set_stored_character_parameters ]] --[[ Line: 52 ]]
            --[[ Upvalues: (ref 1): v_u_6 ]]
            v_u_6:ptry(function() --[[ Line: 53 ]]
                --[[ Upvalues: (copy 1): p_u_21, (ref 2): v_u_6 ]]
                if p_u_21 == nil then
                    return;
                else
                    local v22 = v_u_6:first_child_of_type(p_u_21, "Humanoid")
                    if v22 == nil then
                        return;
                    else
                        local l_RootPart_0 = v22.RootPart
                        if l_RootPart_0 == nil then
                            return;
                        elseif p_u_21.PrimaryPart ~= nil then
                            p_u_21:SetPrimaryPartCFrame(CFrame.new(l_RootPart_0.Position))
                            l_RootPart_0.AssemblyLinearVelocity = Vector3.new(0, 0, 0)
                            l_RootPart_0.Anchored = true
                        end;
                    end;
                end;
            end)
        end;
        local function _(p23) --[[ Name: is_character_okay ]] --[[ Line: 67 ]]
            --[[ Upvalues: (ref 1): v_u_6 ]]
            if p23 == nil then
                return false, "is_character_okay character is nil";
            else
                local v24 = v_u_6:first_child_of_type(p23, "Humanoid")
                if v24 == nil then
                    return false, "is_character_okay player.character has no humanoid";
                elseif v24.RootPart == nil then
                    return false, "is_character_okay player.character has no rootpart";
                elseif v24.Health <= 0 then
                    return false, "is_character_okay player.character has no health";
                elseif v24:GetState() == Enum.HumanoidStateType.Dead then
                    return false, "is_character_okay player.character is dead";
                else
                    return true;
                end;
            end;
        end;
        v12.load_character_for_player = function(p_u_25, p_u_26, p_u_27, p_u_28) --[[ Name: load_character_for_player ]] --[[ Line: 77 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_14, (ref 3): v_u_6, (ref 4): v_u_2, (copy 5): v_u_13, (copy 6): p_u_10, (ref 7): v_u_4, (ref 8): v_u_3, (ref 9): v_u_9 ]]
            if p_u_26.Character ~= nil then
                p_u_26.Character:Destroy()
                p_u_26.Character = nil
            end;
            if v_u_5.ReuseLobbyCharacter == true and v_u_14:contains(p_u_26.UserId) then
                local v29 = v_u_14:get(p_u_26.UserId)
                local v30
                if v29 == nil then
                    v30 = false
                else
                    local v31 = v_u_6:first_child_of_type(v29, "Humanoid")
                    if v31 == nil or (v31.RootPart == nil or v31.Health <= 0) then
                        v30 = false
                    else
                        v30 = v31:GetState() ~= Enum.HumanoidStateType.Dead
                    end;
                end;
                if v30 then
                    if v_u_6:is_dev_build() then
                        v_u_2:puts("ServerPlayerModelCache:load_character_for_player loading lobby stored character for player(%s)", p_u_26.Name)
                    end;
                    local v32 = v_u_14:get(p_u_26.UserId)
                    v_u_14:remove(p_u_26.UserId)
                    p_u_26.Character = v32
                    p_u_27()
                    return;
                end;
            end;
            if v_u_13:contains(p_u_26.UserId) then
                if v_u_6:is_dev_build() then
                    v_u_2:puts("ServerPlayerModelCache:load_character_for_player cloning cached character for player(%s)", p_u_26.Name)
                end;
                local v33 = p_u_25:get_cached_player_model(p_u_26):Clone()
                v33.Name = p_u_26.Name
                p_u_26.Character = v33
                if v_u_5.CharacterModifyAnchorDebug == true then
                    p_u_10._post_fn:enqueue_function(function() --[[ Line: 100 ]]
                        --[[ Upvalues: (copy 1): p_u_26 ]]
                        pcall(function() --[[ Line: 101 ]]
                            --[[ Upvalues: (ref 1): p_u_26 ]]
                            p_u_26.Character.PrimaryPart.Anchored = false
                        end)
                    end, v_u_4:DeltaTimeToTimescale(1))
                end;
                p_u_27()
            else
                local function f_on_character_loaded() --[[ Name: on_character_loaded ]] --[[ Line: 110 ]]
                    --[[ Upvalues: (ref 1): v_u_3, (copy 2): p_u_26, (copy 3): p_u_25, (ref 4): v_u_5, (ref 5): p_u_10, (copy 6): p_u_28, (ref 7): v_u_4, (copy 8): p_u_27 ]]
                    v_u_3:sanitize_model(p_u_26.Character)
                    p_u_25:add_player_to_cache(p_u_26)
                    if v_u_5.CharacterModifyAnchorDebug == true and (p_u_26.Character and p_u_26.Character.PrimaryPart) then
                        p_u_26.Character.PrimaryPart.Anchored = true
                    end;
                    p_u_10._post_fn:enqueue_function(function() --[[ Line: 121 ]]
                        --[[ Upvalues: (ref 1): p_u_28, (ref 2): p_u_26, (ref 3): v_u_5, (ref 4): p_u_10, (ref 5): v_u_4, (ref 6): p_u_27 ]]
                        if p_u_28 == true then
                            local v34 = p_u_26
                            if v34.Character ~= nil then
                                v34.Character:Destroy()
                                v34.Character = nil
                            end;
                        elseif v_u_5.CharacterModifyAnchorDebug == true then
                            p_u_10._post_fn:enqueue_function(function() --[[ Line: 126 ]]
                                --[[ Upvalues: (ref 1): p_u_26 ]]
                                pcall(function() --[[ Line: 127 ]]
                                    --[[ Upvalues: (ref 1): p_u_26 ]]
                                    p_u_26.Character.PrimaryPart.Anchored = false
                                end)
                            end, v_u_4:DeltaTimeToTimescale(1))
                        end;
                        p_u_27()
                    end, 0)
                end;
                local v_u_35 = false
                local v_u_36 = false
                if v_u_6:is_dev_build() then
                    v_u_6:spawn(function() --[[ Line: 140 ]]
                        --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_35, (ref 3): v_u_2, (copy 4): p_u_26, (ref 5): v_u_9, (ref 6): v_u_36, (copy 7): f_on_character_loaded ]]
                        v_u_6:wait(2)
                        if v_u_35 ~= true then
                            v_u_2:warnf("ServerPlayerModelCache:load_character_for_player player(%s) did not load character in time, loading default character", p_u_26.Name)
                            p_u_26.Character = v_u_9:get_default_character_clone()
                            v_u_36 = true
                            f_on_character_loaded()
                        end;
                    end)
                end;
                v_u_6:spawn(function() --[[ Line: 152 ]]
                    --[[ Upvalues: (copy 1): p_u_26, (ref 2): v_u_36, (ref 3): v_u_6, (ref 4): v_u_35, (copy 5): f_on_character_loaded ]]
                    p_u_26:LoadCharacter()
                    if v_u_36 == true then
                        return;
                    end;
                    local v37 = 0
                    local v38 = 0
                    while p_u_26.Character == nil do
                        v37 = v37 + 0.1
                        if v37 > 5 then
                            p_u_26:LoadCharacter()
                            v38 = v38 + 1
                            if v38 > 3 then
                                break;
                            end;
                            v37 = 0
                        end;
                        v_u_6:wait(0.1)
                        if v_u_36 == true then
                            return;
                        end;
                    end;
                    v_u_35 = true
                    f_on_character_loaded()
                end)
            end;
        end;
        v12.store_player_lobby_character = function(p_u_39, p_u_40) --[[ Name: store_player_lobby_character ]] --[[ Line: 177 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_2, (copy 3): v_u_14, (ref 4): v_u_6, (copy 5): p_u_10, (ref 6): v_u_15, (copy 7): l_Folder_0 ]]
            local function f_exit_fail() --[[ Name: exit_fail ]] --[[ Line: 178 ]]
                --[[ Upvalues: (copy 1): p_u_40 ]]
                if p_u_40.Character ~= nil then
                    p_u_40.Character:Destroy()
                    p_u_40.Character = nil
                end;
            end;
            if v_u_5.ReuseLobbyCharacter ~= true then
                return f_exit_fail();
            end;
            if p_u_40.Character == nil then
                v_u_2:warnf("ServerPlayerModelCache:store_player_lobby_character player.character is nil!")
                return f_exit_fail();
            end;
            if v_u_14:contains(p_u_40.UserId) then
                v_u_2:warnf("ServerPlayerModelCache:store_player_lobby_character player already has lobby character stored!")
                v_u_14:get(p_u_40.UserId):Destroy()
                v_u_14:remove(p_u_40.UserId)
            end;
            local l_Character_0 = p_u_40.Character
            v_u_6:ptry(function() --[[ Line: 202 ]]
                --[[ Upvalues: (ref 1): v_u_6, (copy 2): l_Character_0, (copy 3): p_u_39, (copy 4): p_u_40, (ref 5): p_u_10, (ref 6): v_u_15, (ref 7): l_Folder_0, (ref 8): v_u_2, (copy 9): f_exit_fail, (ref 10): v_u_14 ]]
                v_u_6:remove_all_elements_of_model_not_present_in_source(l_Character_0, p_u_39:get_cached_player_model(p_u_40))
                for _, v41 in p_u_10._player_manager:players_key_itr() do
                    if v_u_15 then
                        v_u_15:FireClient(v41, l_Character_0, l_Folder_0, p_u_40.UserId)
                    end;
                end;
                local v42 = l_Character_0
                local v43, v44
                if v42 == nil then
                    v43 = false
                    v44 = "is_character_okay character is nil"
                else
                    local v45 = v_u_6:first_child_of_type(v42, "Humanoid")
                    if v45 == nil then
                        v43 = false
                        v44 = "is_character_okay player.character has no humanoid"
                    elseif v45.RootPart == nil then
                        v43 = false
                        v44 = "is_character_okay player.character has no rootpart"
                    elseif v45.Health <= 0 then
                        v43 = false
                        v44 = "is_character_okay player.character has no health"
                    elseif v45:GetState() == Enum.HumanoidStateType.Dead then
                        v43 = false
                        v44 = "is_character_okay player.character is dead"
                    else
                        v43 = true
                        v44 = nil
                    end;
                end;
                if not v43 then
                    v_u_2:warnf("ServerPlayerModelCache:store_player_lobby_character player.character %s", v44)
                    return f_exit_fail();
                end;
                l_Character_0.Parent = l_Folder_0
                local v_u_46 = l_Character_0
                v_u_6:ptry(function() --[[ Line: 53 ]]
                    --[[ Upvalues: (copy 1): v_u_46, (ref 2): v_u_6 ]]
                    if v_u_46 == nil then
                        return;
                    else
                        local v47 = v_u_6:first_child_of_type(v_u_46, "Humanoid")
                        if v47 == nil then
                            return;
                        else
                            local l_RootPart_1 = v47.RootPart
                            if l_RootPart_1 == nil then
                                return;
                            elseif v_u_46.PrimaryPart ~= nil then
                                v_u_46:SetPrimaryPartCFrame(CFrame.new(l_RootPart_1.Position))
                                l_RootPart_1.AssemblyLinearVelocity = Vector3.new(0, 0, 0)
                                l_RootPart_1.Anchored = true
                            end;
                        end;
                    end;
                end)
                v_u_6:ptry(function() --[[ Line: 219 ]]
                    --[[ Upvalues: (ref 1): l_Character_0 ]]
                    l_Character_0.Humanoid.RootPart.Anchored = true
                end)
                p_u_40.Character = nil
                l_Character_0.Parent = l_Folder_0
                v_u_14:add(p_u_40.UserId, l_Character_0)
                if v_u_6:is_dev_build() then
                    v_u_2:puts("ServerPlayerModelCache:store_player_lobby_character stored lobby character for player(%s) ", p_u_40.Name)
                end;
            end)
        end;
        v12.parent_player_character = function(_, p48) --[[ Name: parent_player_character ]] --[[ Line: 235 ]]
            --[[ Upvalues: (copy 1): p_u_11 ]]
            if p48 and p48.Character then
                p48.Character.Parent = p_u_11
            end;
        end;
        v12.add_player_to_cache = function(_, p_u_49) --[[ Name: add_player_to_cache ]] --[[ Line: 241 ]]
            --[[ Upvalues: (copy 1): v_u_13, (ref 2): v_u_3, (ref 3): v_u_2 ]]
            if v_u_13:contains(p_u_49.UserId) then
                return;
            else
                local function f_add() --[[ Name: add ]] --[[ Line: 246 ]]
                    --[[ Upvalues: (copy 1): p_u_49, (ref 2): v_u_3, (ref 3): v_u_13 ]]
                    p_u_49.Character.Archivable = true
                    v_u_3:sanitize_model(p_u_49.Character)
                    local v50 = p_u_49.Character:Clone()
                    v50.Parent = game.ReplicatedStorage.CharacterProtos
                    v50.Name = tostring(p_u_49.UserId)
                    v_u_13:add(p_u_49.UserId, v50)
                    p_u_49.Character.Archivable = false
                end;
                if p_u_49.Character == nil then
                    v_u_2:warnf("ServerPlayerModelCache::add_player_to_cache ERROR player character is nil!")
                else
                    f_add()
                end;
            end;
        end;
        v12.contains_player = function(_, p51) --[[ Name: contains_player ]] --[[ Line: 265 ]]
            --[[ Upvalues: (copy 1): v_u_13 ]]
            return v_u_13:contains(p51.UserId);
        end;
        v12.get_cached_player_model = function(_, p52) --[[ Name: get_cached_player_model ]] --[[ Line: 269 ]]
            --[[ Upvalues: (copy 1): v_u_13 ]]
            return v_u_13:get(p52.UserId);
        end;
        local l_Folder_1 = Instance.new("Folder")
        l_Folder_1.Name = "StoredPetNPCs"
        l_Folder_1.Parent = game.ReplicatedStorage
        local v_u_53 = v_u_8:new()
        local v_u_54 = v_u_7:new()
        v12.store_lobby_petnpc_character = function(_, p_u_55, p_u_56, p_u_57) --[[ Name: store_lobby_petnpc_character ]] --[[ Line: 281 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_2, (ref 3): v_u_6, (copy 4): p_u_10, (ref 5): v_u_16, (copy 6): l_Folder_1, (copy 7): v_u_53, (copy 8): v_u_54 ]]
            local function f_exit_fail() --[[ Name: exit_fail ]] --[[ Line: 282 ]]
                --[[ Upvalues: (copy 1): p_u_56 ]]
                if p_u_56 ~= nil then
                    p_u_56:Destroy()
                end;
            end;
            if v_u_5.ReuseLobbyPetNPC ~= true then
                return f_exit_fail();
            end;
            if p_u_56 == nil then
                v_u_2:warnf("ServerPlayerModelCache:store_lobby_petnpc_character character is nil!")
                return f_exit_fail();
            end;
            v_u_6:ptry(function() --[[ Line: 293 ]]
                --[[ Upvalues: (ref 1): v_u_6, (copy 2): p_u_56, (ref 3): p_u_10, (ref 4): v_u_16, (ref 5): l_Folder_1, (copy 6): p_u_57, (ref 7): v_u_2, (copy 8): f_exit_fail, (ref 9): v_u_53, (copy 10): p_u_55, (ref 11): v_u_54, (ref 12): v_u_5 ]]
                v_u_6:remove_objects_not_present_in_source(p_u_56)
                for _, v58 in p_u_10._player_manager:players_key_itr() do
                    if v_u_16 then
                        v_u_16:FireClient(v58, p_u_56, l_Folder_1, p_u_57)
                    end;
                end;
                local v59 = p_u_56
                local v60, v61
                if v59 == nil then
                    v60 = false
                    v61 = "is_character_okay character is nil"
                else
                    local v62 = v_u_6:first_child_of_type(v59, "Humanoid")
                    if v62 == nil then
                        v60 = false
                        v61 = "is_character_okay player.character has no humanoid"
                    elseif v62.RootPart == nil then
                        v60 = false
                        v61 = "is_character_okay player.character has no rootpart"
                    elseif v62.Health <= 0 then
                        v60 = false
                        v61 = "is_character_okay player.character has no health"
                    elseif v62:GetState() == Enum.HumanoidStateType.Dead then
                        v60 = false
                        v61 = "is_character_okay player.character is dead"
                    else
                        v60 = true
                        v61 = nil
                    end;
                end;
                if not v60 then
                    v_u_2:warnf("ServerPlayerModelCache:store_lobby_petnpc_character character %s", v61)
                    return f_exit_fail();
                end;
                p_u_56.Parent = l_Folder_1
                local v_u_63 = p_u_56
                v_u_6:ptry(function() --[[ Line: 53 ]]
                    --[[ Upvalues: (copy 1): v_u_63, (ref 2): v_u_6 ]]
                    if v_u_63 == nil then
                        return;
                    else
                        local v64 = v_u_6:first_child_of_type(v_u_63, "Humanoid")
                        if v64 == nil then
                            return;
                        else
                            local l_RootPart_2 = v64.RootPart
                            if l_RootPart_2 == nil then
                                return;
                            elseif v_u_63.PrimaryPart ~= nil then
                                v_u_63:SetPrimaryPartCFrame(CFrame.new(l_RootPart_2.Position))
                                l_RootPart_2.AssemblyLinearVelocity = Vector3.new(0, 0, 0)
                                l_RootPart_2.Anchored = true
                            end;
                        end;
                    end;
                end)
                v_u_53:push_back_to(p_u_55, p_u_56)
                v_u_54:push_back(p_u_56)
                if v_u_54:count() > v_u_5.LobbyPetNPCStoreLRUCount then
                    local v65 = v_u_54:pop_front()
                    for _, v66 in v_u_53:key_itr() do
                        v66:remove(v65)
                    end;
                    if v_u_6:is_dev_build() then
                        v_u_2:warnf("ServerPlayerModelCache:store_lobby_petnpc_character _stored_model_lru full removing(%s)", v65:GetFullName())
                    end;
                    v65:Destroy()
                end;
                if v_u_6:is_dev_build() then
                    v_u_2:puts("ServerPlayerModelCache:store_lobby_petnpc_character stored lobby petnpc(%d)<%d> pos(%.2f,%.2f,%.2f)", p_u_55, v_u_53:list_of(p_u_55):count(), p_u_56.PrimaryPart.Position.X, p_u_56.PrimaryPart.Position.Y, p_u_56.PrimaryPart.Position.Z)
                end;
            end)
        end;
        v12.load_stored_lobby_petnpc = function(_, p67) --[[ Name: load_stored_lobby_petnpc ]] --[[ Line: 337 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_53, (copy 3): v_u_54, (ref 4): v_u_6 ]]
            if v_u_5.ReuseLobbyPetNPC ~= true then
                return nil;
            end;
            if v_u_53:list_of(p67):count() == 0 then
                return nil;
            end;
            local v68 = v_u_53:pop_front_from(p67)
            v_u_54:remove(v68)
            local v69
            if v68 == nil then
                v69 = false
            else
                local v70 = v_u_6:first_child_of_type(v68, "Humanoid")
                if v70 == nil or (v70.RootPart == nil or v70.Health <= 0) then
                    v69 = false
                else
                    v69 = v70:GetState() ~= Enum.HumanoidStateType.Dead
                end;
            end;
            if v69 == true then
                return v68;
            end;
            v68:Destroy()
            return nil;
        end;
        return v12;
    end
};
