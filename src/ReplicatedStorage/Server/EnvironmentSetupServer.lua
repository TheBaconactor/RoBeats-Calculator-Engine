-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:13 PM
-- Cached decompilation

local v1 = require(game.ReplicatedStorage.Shared.NoCollideGroup)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_3 = require(game.ReplicatedStorage.Pets.PetInfoBase)
local v_u_4 = require(game.ReplicatedStorage.GameStage.GameStageDatabase)
local v_u_5 = require(game.ReplicatedStorage.Server.ServerEnvironmentDecorationSetup)
local v_u_6 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_7 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_8 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_9 = require(game.ReplicatedStorage.Shared.SPDict)
if v_u_8:is_dev_build() and game:GetService("RunService"):IsClient() then
    v_u_7:errf("EnvironmentSetupServer called on client")
end;
local v10 = {}
local v_u_11 = nil
local v_u_12 = nil
local v_u_13 = nil
local v_u_14 = nil
local v_u_15 = nil
local v_u_16 = v1:new()
v10.get_player_collision_group = function(_) --[[ Name: get_player_collision_group ]] --[[ Line: 27 ]]
    --[[ Upvalues: (copy 1): v_u_16 ]]
    return v_u_16;
end;
v10.initial_setup = function(_) --[[ Name: initial_setup ]] --[[ Line: 31 ]]
    --[[ Upvalues: (copy 1): v_u_16, (ref 2): v_u_13, (copy 3): v_u_6, (ref 4): v_u_11, (ref 5): v_u_12, (ref 6): v_u_14, (copy 7): v_u_3, (copy 8): v_u_4, (copy 9): v_u_8, (copy 10): v_u_5, (copy 11): v_u_7, (ref 12): v_u_15 ]]
    local function _(p17) --[[ Name: add_children_to_player_collision_group ]] --[[ Line: 32 ]]
        --[[ Upvalues: (ref 1): v_u_16 ]]
        for _, v18 in pairs(p17:GetChildren()) do
            v_u_16:add_to_group(v18)
        end;
    end;
    v_u_13 = game.Workspace:FindFirstChild("Environment")
    if v_u_13 == nil then
        v_u_13 = game.ReplicatedStorage:FindFirstChild("Environment")
    end;
    v_u_6:is_non_nil(v_u_13)
    for _, v19 in pairs(v_u_13.ClothingShop.ClothingModels:GetChildren()) do
        v_u_16:add_to_group(v19)
    end;
    v_u_13.Parent = game.Workspace
    v_u_11 = game.Workspace.LobbyCharacters
    v_u_12 = game.Workspace.LobbyFollowNPCs
    v_u_14 = game.Workspace:FindFirstChild("LobbyElementProtos")
    if v_u_14 == nil then
        v_u_14 = game.ReplicatedStorage:FindFirstChild("LobbyElementProtos")
    end;
    v_u_3:do_environment_setup()
    v_u_4:setup_game_stages()
    local v20, v21 = v_u_8:try(function() --[[ Line: 57 ]]
        --[[ Upvalues: (ref 1): v_u_5 ]]
        v_u_5:setup_environment_decorations()
    end)
    if v20 ~= true then
        if v_u_8:is_dev_build() then
            v_u_7:errf("ServerEnvironmentDecorationSetup:initial_setup failed[%s]\n%s", v21.Error, v21.StackTrace)
        else
            v_u_7:warnf("ServerEnvironmentDecorationSetup:initial_setup failed[%s]\n%s", v21.Error, v21.StackTrace)
        end;
    end;
    v_u_15 = game.ReplicatedStorage.CharacterProtos.Default
end;
v10.post_server_api_loaded_setup = function(_, p_u_22) --[[ Name: post_server_api_loaded_setup ]] --[[ Line: 71 ]]
    --[[ Upvalues: (copy 1): v_u_8, (copy 2): v_u_5, (copy 3): v_u_7, (copy 4): v_u_9, (copy 5): v_u_2 ]]
    local v23, v24 = v_u_8:try(function() --[[ Line: 72 ]]
        --[[ Upvalues: (ref 1): v_u_5, (copy 2): p_u_22 ]]
        v_u_5:server_loaded_setup(p_u_22)
    end)
    if v23 ~= true then
        if v_u_8:is_dev_build() then
            v_u_7:errf("EnvironmentSetupServer:post_server_api_loaded_setup failed[%s]\n%s", v24.Error, v24.StackTrace)
        else
            v_u_7:warnf("EnvironmentSetupServer:post_server_api_loaded_setup failed[%s]\n%s", v24.Error, v24.StackTrace)
        end;
    end;
    local v_u_25 = v_u_9:new()
    v_u_8:try(function() --[[ Line: 85 ]]
        --[[ Upvalues: (copy 1): v_u_25 ]]
        local function f_add_obj_and_children(p26) --[[ Name: add_obj_and_children ]] --[[ Line: 86 ]]
            --[[ Upvalues: (ref 1): v_u_25, (copy 2): f_add_obj_and_children ]]
            v_u_25:add_set(p26)
            for _, v27 in pairs(p26:GetChildren()) do
                f_add_obj_and_children(v27)
            end;
        end;
        f_add_obj_and_children(game)
    end)
    v_u_7:puts("EnvironmentSetupServer search_expected_objects_root expected object count: %d", v_u_25:count())
    v_u_2:for_each(v_u_2:new({
        game.Workspace,
        game.Workspace.Environment,
        game.Workspace.Camera,
        game.Workspace.Terrain,
        game.Workspace.IntersectZones,
        game.Workspace.LobbyAnchors,
        game.ReplicatedFirst,
        game.ReplicatedStorage,
        game.Lighting,
        game.StarterGui,
        game.StarterPack,
        game.StarterPlayer,
        game.StarterPlayer.StarterCharacterScripts,
        game.StarterPlayer.StarterPlayerScripts,
        game.Teams,
        game.SoundService
    }), function(p_u_28) --[[ Line: 115 ]]
        --[[ Upvalues: (ref 1): v_u_8, (copy 2): v_u_25, (ref 3): v_u_7 ]]
        v_u_8:spawn(function() --[[ Line: 116 ]]
            --[[ Upvalues: (copy 1): p_u_28, (ref 2): v_u_25, (ref 3): v_u_7, (ref 4): v_u_8 ]]
            while true do
                for _, v29 in pairs(p_u_28:GetChildren()) do
                    if v_u_25:contains(v29) ~= true then
                        v_u_7:warnf("EnvironmentSetupServer search_expected_objects_root removing unexpected object: %s", v29:GetFullName())
                        v29.Parent = nil
                    end;
                end;
                v_u_8:wait((v_u_8:rand_rangef(10, 20)))
            end;
        end)
        v_u_8:wait(0.25)
    end)
end;
v10.get_lobby_characters_folder = function(_) --[[ Name: get_lobby_characters_folder ]] --[[ Line: 132 ]]
    --[[ Upvalues: (ref 1): v_u_11 ]]
    return v_u_11;
end;
v10.get_lobby_follow_npcs_folder = function(_) --[[ Name: get_lobby_follow_npcs_folder ]] --[[ Line: 136 ]]
    --[[ Upvalues: (ref 1): v_u_12 ]]
    return v_u_12;
end;
v10.get_lobby_element_protos_folder = function(_) --[[ Name: get_lobby_element_protos_folder ]] --[[ Line: 140 ]]
    --[[ Upvalues: (ref 1): v_u_14 ]]
    return v_u_14;
end;
v10.get_environment = function(_) --[[ Name: get_environment ]] --[[ Line: 144 ]]
    --[[ Upvalues: (ref 1): v_u_13 ]]
    return v_u_13;
end;
v10.get_default_character_clone = function(_) --[[ Name: get_default_character_clone ]] --[[ Line: 148 ]]
    --[[ Upvalues: (ref 1): v_u_15 ]]
    return v_u_15:Clone();
end;
return v10;
