-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:04 PM
-- Time elapsed: 9 milliseconds

return {
    ["new"] = function(_) --[[ Name: new ]] --[[ Line: 3 ]]
        return {
            ["evt_report_error"] = function(_, _) end,
            ["player_name_sub"] = function(_, p1) --[[ Name: player_name_sub ]] --[[ Line: 8 ]]
                for _, v2 in pairs(game.Players:GetPlayers()) do
                    p1 = string.gsub(p1, v2.Name, "[[RBXNAME]]")
                end;
                return p1;
            end
        };
    end,
    ["LOG_DEFAULT"] = 0,
    ["LOG_ERROR_GUILD_DATASTORE"] = 1,
    ["LOG_DEV_GUILD_DATASTORE"] = 2
};
