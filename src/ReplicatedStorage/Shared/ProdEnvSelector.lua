-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:05 PM
-- Cached decompilation

local v1 = require(game.ReplicatedStorage.Shared.SPDict)
local l_Players_0 = game.Players
local v_u_2 = {
    ["ENV_LOCAL"] = 0,
    ["ENV_DEV"] = 1,
    ["ENV_PROD"] = 2
}
local l_JobId_0 = game.JobId
v_u_2.get_env = function(_) --[[ Name: get_env ]] --[[ Line: 12 ]]
    --[[ Upvalues: (ref 1): l_JobId_0, (copy 2): v_u_2 ]]
    if l_JobId_0 == "" then
        return v_u_2.ENV_LOCAL;
    elseif game.PlaceId == 698448212 then
        return v_u_2.ENV_PROD;
    else
        return v_u_2.ENV_DEV;
    end;
end;
v_u_2.client_wait_for_update = function(_, p_u_3) --[[ Name: client_wait_for_update ]] --[[ Line: 22 ]]
    --[[ Upvalues: (ref 1): l_JobId_0, (copy 2): v_u_2 ]]
    local v_u_4 = true
    local v_u_5 = nil
    local v_u_6 = {}
    v_u_5 = game.ReplicatedStorage.Events.ProdEnvSelectorRemoteEvent.OnClientEvent:connect(function(p7, p8, p9) --[[ Line: 26 ]]
        --[[ Upvalues: (ref 1): v_u_6, (ref 2): l_JobId_0, (ref 3): v_u_4, (ref 4): v_u_5, (copy 5): p_u_3 ]]
        v_u_6 = p8
        l_JobId_0 = p7
        print(string.format("[Client] ProdEnvSelector client_wait_for_update game_jobid(%s)", (tostring(l_JobId_0))))
        v_u_4 = false
        if v_u_5 ~= nil then
            v_u_5:Disconnect()
            v_u_5 = nil
        end;
        p_u_3:load_private_keys(p9)
    end)
    local v10 = v_u_6
    local v11 = v_u_5
    while v_u_4 == true do
        print("[Client] ProdEnvSelector client_wait_for_update waiting...")
        wait(0.1)
    end;
    game.ReplicatedStorage.Events.ProdEnvSelectorRemoteEvent:FireServer()
    local v12 = v_u_2:get_env()
    if v12 == v_u_2.ENV_LOCAL then
        print("[Client] env: LOCAL")
    elseif v12 == v_u_2.ENV_PROD then
        print("[Client] env: PROD")
    else
        print("[Client] env: DEV")
    end;
    if v11 ~= nil then
        v11:Disconnect()
    end;
    game.ReplicatedStorage.Events.ProdEnvSelectorRemoteEvent.Parent = nil
    return v10;
end;
local v_u_13 = v1:new()
local v_u_14 = {}
v_u_2.server_init = function(_, p15) --[[ Name: server_init ]] --[[ Line: 64 ]]
    --[[ Upvalues: (ref 1): v_u_14, (copy 2): v_u_13 ]]
    v_u_14 = p15
    game.ReplicatedStorage.Events.ProdEnvSelectorRemoteEvent.OnServerEvent:connect(function(p16) --[[ Line: 66 ]]
        --[[ Upvalues: (ref 1): v_u_13 ]]
        print("[Server] ack ProdEnvSelectorRemoteEvent from", p16.UserId)
        v_u_13:remove(p16.UserId)
    end)
end;
v_u_2.server_push_update_to_player = function(_, p_u_17, p_u_18, p_u_19) --[[ Name: server_push_update_to_player ]] --[[ Line: 73 ]]
    --[[ Upvalues: (copy 1): v_u_13, (copy 2): l_Players_0, (ref 3): l_JobId_0, (ref 4): v_u_14 ]]
    v_u_13:add(p_u_17.UserId, true)
    spawn(function() --[[ Line: 75 ]]
        --[[ Upvalues: (copy 1): p_u_18, (copy 2): p_u_17, (ref 3): v_u_13, (ref 4): l_Players_0, (ref 5): l_JobId_0, (ref 6): v_u_14, (copy 7): p_u_19 ]]
        local v20 = p_u_18:generate_keys_for_playerid(p_u_17.UserId)
        while v_u_13:contains(p_u_17.UserId) do
            if l_Players_0:GetPlayerByUserId(p_u_17.UserId) == nil then
                v_u_13:remove(p_u_17.UserId)
                return;
            end;
            game.ReplicatedStorage.Events.ProdEnvSelectorRemoteEvent:FireClient(p_u_17, l_JobId_0, v_u_14, v20)
            wait(1.5)
        end;
        if p_u_19 then
            p_u_19()
        end;
    end)
end;
return v_u_2;
