-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:02 PM
-- Cached decompilation

require(game.ReplicatedStorage.Shared.SPDict)
local v1 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_2 = require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.Shared.SPUtil)
local v3 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_4 = nil
local v_u_5 = nil
v3:require_client(function() --[[ Line: 9 ]]
    --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_5 ]]
    v_u_4 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
    v_u_5 = require(game.ReplicatedStorage.LobbyDecoration.RegisterLobbyDecoration)
end)
local v6 = {}
local v_u_7 = v1:new()
v6.setup_environment_decorations = function(_, p_u_8) --[[ Name: setup_environment_decorations ]] --[[ Line: 17 ]]
    --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_4, (copy 3): v_u_2, (copy 4): v_u_7 ]]
    local v_u_9 = v_u_5:get_class_to_name_dict()
    local v10 = v_u_4:get_lobby_environment()
    if v10 == nil then
        return v_u_2:warnf("LocalEnvironmentDecorationSetup:setup_environment_decorations no lobby environment");
    end;
    local v_u_11 = v10:FindFirstChild("PlacedLobbyDecorations")
    if v_u_11 == nil then
        return v_u_2:warnf("LocalEnvironmentDecorationSetup:setup_environment_decorations no PlacedLobbyDecorations");
    end;
    local v15, v16 = pcall(function() --[[ Line: 26 ]]
        --[[ Upvalues: (copy 1): v_u_11, (copy 2): v_u_9, (ref 3): v_u_7, (copy 4): p_u_8 ]]
        for _, v12 in pairs(v_u_11:GetChildren()) do
            for _, v13 in pairs(v12:GetChildren()) do
                local l_Name_0 = v13.Name
                if v_u_9:contains(l_Name_0) then
                    v_u_7:push_back(v_u_9:get(l_Name_0):new(v13))
                end;
            end;
        end;
        for _, v14 in v_u_7:key_itr() do
            v14:on_client_startup(p_u_8)
        end;
    end)
    if not v15 then
        v_u_2:warnf("LocalEnvironmentDecorationSetup:setup_environment_decorations failed to setup decorations: %s", v16)
    end;
end;
return v6;
